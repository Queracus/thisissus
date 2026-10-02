"""Worker job media.derive: WebP display + thumb for photos. Derivatives NEVER carry EXIF/GPS, so anything served
through a share is location-free; the original's EXIF is parsed into media.exif for the owners only."""
import io

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
    variants = {}
    for name, size in PHOTO_SIZES.items():
        v = img.copy()
        v.info.pop("exif", None)
        v.thumbnail((size, size))
        buf = io.BytesIO()
        v.save(buf, "WEBP", quality=82, exif=b"")
        variants[name] = buf.getvalue()
    return {"width": img.width, "height": img.height, "exif": meta, "variants": variants}


async def derive_photo(conn: asyncpg.Connection, payload: dict) -> None:
    original = await conn.fetchrow("SELECT * FROM media WHERE id = $1", payload["media_id"])
    if not original or original["deleted_at"]:
        return
    try:
        result = await run_in_threadpool(process_photo, await read_all(conn, original["id"]))
    except (UnidentifiedImageError, OSError):
        await conn.execute("UPDATE media SET status = 'failed' WHERE id = $1", original["id"])
        return
    await conn.execute("DELETE FROM media WHERE parent_id = $1", original["id"])  # idempotent re-run
    for variant, data in result["variants"].items():
        await save_bytes(conn, original["space_id"], original["created_by"], "photo", variant, "image/webp", data, parent_id=original["id"])
    await conn.execute("UPDATE media SET status = 'ready', width = $2, height = $3, exif = $4 WHERE id = $1",
                       original["id"], result["width"], result["height"], result["exif"])
