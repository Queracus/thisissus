import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.deps import current_user
from app.db import get_conn

router = APIRouter(prefix="/notifications")


class ReadIn(BaseModel):
    ids: list[int] | None = None  # None = mark all as read


@router.get("")
async def list_notifications(user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    items = await conn.fetch(
        "SELECT id, kind, payload, created_at, read_at FROM notifications WHERE user_id = $1 ORDER BY id DESC LIMIT 50", user["id"])
    unread = await conn.fetchval("SELECT count(*) FROM notifications WHERE user_id = $1 AND read_at IS NULL", user["id"])
    return {"unread": unread, "items": [dict(r) for r in items]}


@router.post("/read")
async def mark_read(body: ReadIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await conn.execute(
        "UPDATE notifications SET read_at = now() WHERE user_id = $1 AND read_at IS NULL AND ($2::bigint[] IS NULL OR id = ANY($2::bigint[]))",
        user["id"], body.ids)
    return {"ok": True}
