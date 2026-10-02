"""Photos and videos attached to an owner (a date or a recipe). One implementation, mounted once per owner type.

    gallery_router("/dates", "date_media", "date_id", visible_date)
    gallery_router("/recipes", "recipe_media", "recipe_id", visible_recipe)
"""
import asyncpg
from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel, Field

from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError
from app.jobs import enqueue
from app.media import store

MEDIA_TYPES = {"image/jpeg": "photo", "image/png": "photo", "image/webp": "photo", "image/heic": "photo",
               "video/mp4": "video", "video/quicktime": "video"}


class CaptionIn(BaseModel):
    caption: str | None = Field(default=None, max_length=300)


class OrderIn(BaseModel):
    media_ids: list[int]


async def gallery(conn: asyncpg.Connection, join_table: str, fk: str, owner_id: int) -> list[dict]:
    rows = await conn.fetch(
        f"""SELECT m.id, m.kind, m.status, m.width, m.height, m.duration_s, j.caption, j.position
            FROM {join_table} j JOIN media m ON m.id = j.media_id
            WHERE j.{fk} = $1 AND m.deleted_at IS NULL ORDER BY j.position, m.id""", owner_id)
    return [dict(r) for r in rows]


async def date_photos(conn: asyncpg.Connection, date_id: int) -> list[dict]:
    return await gallery(conn, "date_media", "date_id", date_id)


def gallery_router(prefix: str, join_table: str, fk: str, visible) -> APIRouter:
    """visible(conn, user_id, owner_id) → owner row with space_id, or raises 404."""
    router = APIRouter(prefix=prefix)

    async def attached(conn: asyncpg.Connection, owner_id: int, media_id: int) -> None:
        if not await conn.fetchval(
                f"SELECT 1 FROM {join_table} j JOIN media m ON m.id = j.media_id WHERE j.{fk} = $1 AND j.media_id = $2 AND m.deleted_at IS NULL",
                owner_id, media_id):
            raise ApiError(404, "media.not_found")

    @router.post("/{owner_id}/photos")
    async def upload(owner_id: int, file: UploadFile, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
        owner = await visible(conn, user["id"], owner_id)
        async with conn.transaction():
            media_id, kind = await store.save_upload(conn, owner["space_id"], user["id"], file, MEDIA_TYPES)
            await conn.execute(
                f"INSERT INTO {join_table} ({fk}, media_id, position) SELECT $1, $2, coalesce(max(position) + 1, 0) FROM {join_table} WHERE {fk} = $1",
                owner_id, media_id)
            await enqueue(conn, "media.derive", {"media_id": media_id})
        return {"id": media_id, "kind": kind, "status": "pending"}

    @router.patch("/{owner_id}/photos/{media_id}")
    async def set_caption(owner_id: int, media_id: int, body: CaptionIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
        await visible(conn, user["id"], owner_id)
        await attached(conn, owner_id, media_id)
        await conn.execute(f"UPDATE {join_table} SET caption = $3 WHERE {fk} = $1 AND media_id = $2", owner_id, media_id, body.caption)
        return {"ok": True}

    @router.put("/{owner_id}/photos/order")
    async def set_order(owner_id: int, body: OrderIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
        await visible(conn, user["id"], owner_id)
        await conn.executemany(f"UPDATE {join_table} SET position = $3 WHERE {fk} = $1 AND media_id = $2",
                               [(owner_id, m, i) for i, m in enumerate(body.media_ids)])
        return {"ok": True}

    @router.delete("/{owner_id}/photos/{media_id}")
    async def remove(owner_id: int, media_id: int, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
        await visible(conn, user["id"], owner_id)
        await attached(conn, owner_id, media_id)
        await conn.execute("UPDATE media SET deleted_at = now() WHERE id = $1", media_id)  # trash; purged later
        return {"ok": True}

    return router


def _visible_date(conn, user_id, date_id):
    from app.routers.dates import visible_date  # dates imports this module for date_photos
    return visible_date(conn, user_id, date_id)


router = gallery_router("/dates", "date_media", "date_id", _visible_date)
