"""Worker job media.derive.
Photos → WebP display + thumb. Videos → H.264/AAC MP4 (plays everywhere, seekable) + WebP poster + thumb.
Derivatives NEVER carry EXIF/GPS/location metadata, so anything served through a share is location-free;
the original's EXIF is parsed into media.exif for the owners only."""
import io
import json
import subprocess
import tempfile
from pathlib import Path

import asyncpg
import pillow_heif
from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from app.media.store import read_all, save_bytes

pillow_heif.register_heif_opener()
PHOTO_SIZES = {"display": 2048, "thumb": 400}


def _dms(values, ref) -> float:
    deg, minutes, seconds = (float(v) for v in values)
    sign = -1 if ref in ("S", "W") else 1
    return sign * (deg + minutes / 60 + seconds / 3600)


def _exif_meta(img: Image.Image) -> dict:
    exif = img.getexif()
    meta = {}
    taken = exif.get_ifd(ExifTags.IFD.Exif).get(ExifTags.Base.DateTimeOriginal) or exif.get(ExifTags.Base.DateTime)
    if taken:
        meta["taken_at"] = str(taken)
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    try:
        meta["lat"], meta["lon"] = _dms(gps[2], gps[1]), _dms(gps[4], gps[3])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        pass
    return meta


def process_photo(data: bytes) -> dict:
    """CPU-bound (runs in a thread): parse EXIF, rotate upright, encode metadata-free WebPs."""
    img = Image.open(io.BytesIO(data))
    meta = _exif_meta(img)
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    variants = {name: _webp(img, size) for name, size in PHOTO_SIZES.items()}
    return {"width": img.width, "height": img.height, "exif": meta, "variants": variants}


def _webp(img: Image.Image, size: int) -> bytes:
    v = img.copy()
    v.info.pop("exif", None)
    v.thumbnail((size, size))
    buf = io.BytesIO()
    v.save(buf, "WEBP", quality=82, exif=b"")
    return buf.getvalue()


def _run(args: list, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in args], capture_output=True, check=True, timeout=timeout)


def process_video(data: bytes) -> dict:
    """CPU-bound (runs in a thread): transcode with ffmpeg; -map_metadata -1 drops location and every other tag."""
    with tempfile.TemporaryDirectory() as tmp:
        src, out, frame = Path(tmp) / "in", Path(tmp) / "out.mp4", Path(tmp) / "poster.png"
        src.write_bytes(data)
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-map_metadata", "-1", "-map_chapters", "-1",
              "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
              "-vf", "scale='min(1920,iw)':-2", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out])
        info = json.loads(_run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height:format=duration", "-of", "json", out]).stdout)
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", out, "-frames:v", "1", frame])
        with Image.open(frame) as poster:
            poster.load()
            variants = {"poster": _webp(poster, 1280), "thumb": _webp(poster, 400)}
        return {"width": info["streams"][0]["width"], "height": info["streams"][0]["height"],
                "duration_s": float(info["format"]["duration"]), "mp4": out.read_bytes(), "variants": variants}


async def derive_media(conn: asyncpg.Connection, payload: dict) -> None:
    original = await conn.fetchrow("SELECT * FROM media WHERE id = $1", payload["media_id"])
    if not original or original["deleted_at"]:
        return
    data = await read_all(conn, original["id"])
    is_video = original["kind"] == "video"
    try:
        result = await run_in_threadpool(process_video if is_video else process_photo, data)
    except (UnidentifiedImageError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, KeyError):
        await conn.execute("UPDATE media SET status = 'failed' WHERE id = $1", original["id"])
        return
    await conn.execute("DELETE FROM media WHERE parent_id = $1", original["id"])  # idempotent re-run

    async def keep(variant: str, mime: str, blob: bytes) -> None:
        await save_bytes(conn, original["space_id"], original["created_by"], original["kind"], variant, mime, blob, parent_id=original["id"])

    for variant, blob in result["variants"].items():
        await keep(variant, "image/webp", blob)
    if is_video:
        await keep("mp4", "video/mp4", result["mp4"])
    await conn.execute("UPDATE media SET status = 'ready', width = $2, height = $3, exif = $4, duration_s = $5 WHERE id = $1",
                       original["id"], result["width"], result["height"], result.get("exif"), result.get("duration_s"))
