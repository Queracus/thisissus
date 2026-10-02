import asyncpg
from fastapi import APIRouter, Depends

from app import trash
from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError
from app.policy import active_space, require_member

router = APIRouter(prefix="/trash")


async def _trashed(conn: asyncpg.Connection, user_id: int, kind: str, item_id: int) -> None:
    """404 unless the item is in the trash of a space the user belongs to."""
    space_id = await trash.item_space(conn, kind, item_id)
    if space_id is None:
        raise ApiError(404, "trash.not_found")
    await require_member(conn, user_id, space_id, "write")


@router.get("")
async def list_trash(space: asyncpg.Record = Depends(active_space), conn: asyncpg.Connection = Depends(get_conn)):
    return await trash.list_trash(conn, space["id"])


@router.post("/{kind}/{item_id}/restore")
async def restore(kind: str, item_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await _trashed(conn, user["id"], kind, item_id)
    await trash.restore(conn, kind, item_id)
    return {"ok": True}


@router.delete("/{kind}/{item_id}")
async def purge(kind: str, item_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await _trashed(conn, user["id"], kind, item_id)
    async with conn.transaction():
        await trash.purge(conn, kind, item_id)
    return {"ok": True}
