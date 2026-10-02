"""Worker job media.export: every original photo/video as plain files, browsable without the app.

    EXPORT_DIR/<space>/zmenki/YYYY/MM/YYYY-MM-DD <date title>/01-<caption>.jpg
    EXPORT_DIR/<space>/recepti/<recipe title>/01.jpg

Re-runs only write what's missing (same name + same size = skipped). Trashed items are left out.
"""
import re
from pathlib import Path
from zoneinfo import ZoneInfo

import asyncpg

from app import config

EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/heic": ".heic", "video/mp4": ".mp4", "video/quicktime": ".mov"}
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def safe_name(text: str, limit: int = 80) -> str:
    """A file/folder name that is valid on Windows and Linux."""
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", text).strip().rstrip(". ")[:limit]
    if name.upper() in RESERVED:
        name = "_" + name
    return name or "_"


async def _write(conn: asyncpg.Connection, media: asyncpg.Record, path: Path) -> bool:
    """Write a media original to path unless an identical-size file is already there. Returns True if written."""
    if path.exists() and path.stat().st_size == media["size"]:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    with tmp.open("wb") as f:
        seq = 0
        while rows := await conn.fetch("SELECT data FROM media_chunks WHERE media_id = $1 AND seq >= $2 ORDER BY seq LIMIT 8", media["id"], seq):
            for r in rows:
                f.write(r["data"])
            seq += len(rows)
    tmp.replace(path)
    return True


async def _export_gallery(conn, join_table: str, fk: str, owner_id: int, folder: Path, with_caption: bool) -> tuple[int, int]:
    files = written = 0
    photos = await conn.fetch(
        f"""SELECT m.id, m.mime, m.size, j.caption FROM {join_table} j JOIN media m ON m.id = j.media_id
            WHERE j.{fk} = $1 AND m.deleted_at IS NULL ORDER BY j.position, m.id""", owner_id)
    for n, m in enumerate(photos, 1):
        name = f"{n:02d}" + (f"-{safe_name(m['caption'], 60)}" if with_caption and m["caption"] else "") + EXT.get(m["mime"], "")
        files += 1
        written += await _write(conn, m, folder / name)
    return files, written


async def export_all(conn: asyncpg.Connection, payload: dict) -> dict:
    root, tz = Path(config.EXPORT_DIR), ZoneInfo(config.TIMEZONE)
    files = written = 0
    for space in await conn.fetch("SELECT id, name FROM spaces ORDER BY id"):
        base = root / safe_name(space["name"])
        for d in await conn.fetch("SELECT id, title, starts_at FROM dates WHERE space_id = $1 AND deleted_at IS NULL", space["id"]):
            day = d["starts_at"].astimezone(tz)
            folder = base / "zmenki" / f"{day:%Y}" / f"{day:%m}" / f"{day:%Y-%m-%d} {safe_name(d['title'])}"
            f, w = await _export_gallery(conn, "date_media", "date_id", d["id"], folder, with_caption=True)
            files, written = files + f, written + w
        for r in await conn.fetch("SELECT id, title FROM recipes WHERE space_id = $1 AND deleted_at IS NULL", space["id"]):
            f, w = await _export_gallery(conn, "recipe_media", "recipe_id", r["id"], base / "recepti" / safe_name(r["title"]), with_caption=False)
            files, written = files + f, written + w
    await conn.execute("INSERT INTO export_runs (files, written) VALUES ($1, $2)", files, written)
    return {"files": files, "written": written}
