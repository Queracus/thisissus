"""Photos (and later videos) attached to a date."""
import asyncpg
from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel, Field

from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError
from app.jobs import enqueue
from app.media import store
from app.routers.dates import visible_date

router = APIRouter(prefix="/dates")
MEDIA_TYPES = {"image/jpeg": "photo", "image/png": "photo", "image/webp": "photo", "image/heic": "photo",
               "video/mp4": "video", "video/quicktime": "video"}


class CaptionIn(BaseModel):
    caption: str | None = Field(default=None, max_length=300)


class OrderIn(BaseModel):
    media_ids: list[int]


async def date_photos(conn: asyncpg.Connection, date_id: int) -> list[dict]:
    rows = await conn.fetch(
        """SELECT m.id, m.kind, m.status, m.width, m.height, m.duration_s, dm.caption, dm.position
           FROM date_media dm JOIN media m ON m.id = dm.media_id
           WHERE dm.date_id = $1 AND m.deleted_at IS NULL ORDER BY dm.position, m.id""", date_id)
    return [dict(r) for r in rows]


async def _attached(conn: asyncpg.Connection, date_id: int, media_id: int) -> None:
    if not await conn.fetchval("SELECT 1 FROM date_media dm JOIN media m ON m.id = dm.media_id WHERE dm.date_id = $1 AND dm.media_id = $2 AND m.deleted_at IS NULL",
                               date_id, media_id):
        raise ApiError(404, "media.not_found")


@router.post("/{date_id}/photos")
async def upload_photo(date_id: int, file: UploadFile, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    date = await visible_date(conn, user["id"], date_id)
    async with conn.transaction():
        media_id, kind = await store.save_upload(conn, date["space_id"], user["id"], file, MEDIA_TYPES)
        await conn.execute(
            "INSERT INTO date_media (date_id, media_id, position) SELECT $1, $2, coalesce(max(position) + 1, 0) FROM date_media WHERE date_id = $1",
            date_id, media_id)
        await enqueue(conn, "media.derive", {"media_id": media_id})
    return {"id": media_id, "kind": kind, "status": "pending"}


@router.patch("/{date_id}/photos/{media_id}")
async def set_caption(date_id: int, media_id: int, body: CaptionIn, user: asyncpg.Record = Depends(current_user),
                      conn: asyncpg.Connection = Depends(get_conn)):
    await visible_date(conn, user["id"], date_id)
    await _attached(conn, date_id, media_id)
    await conn.execute("UPDATE date_media SET caption = $3 WHERE date_id = $1 AND media_id = $2", date_id, media_id, body.caption)
    return {"ok": True}


@router.put("/{date_id}/photos/order")
async def set_order(date_id: int, body: OrderIn, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await visible_date(conn, user["id"], date_id)
    await conn.executemany("UPDATE date_media SET position = $3 WHERE date_id = $1 AND media_id = $2",
                           [(date_id, m, i) for i, m in enumerate(body.media_ids)])
    return {"ok": True}


@router.delete("/{date_id}/photos/{media_id}")
async def remove_photo(date_id: int, media_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await visible_date(conn, user["id"], date_id)
    await _attached(conn, date_id, media_id)
    await conn.execute("UPDATE media SET deleted_at = now() WHERE id = $1", media_id)  # trash; purged later
    return {"ok": True}
