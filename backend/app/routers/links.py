"""Public, read-only secret-link views (no account): /api/s/{token}/... Only derivatives of covered items are served."""
import asyncpg
from fastapi import APIRouter, Depends, Request

from app import sharing
from app.db import get_conn
from app.errors import ApiError
from app.routers.media import DERIVATIVE_SQL, respond
from app.routers.shares import EntityType, shared_payload

router = APIRouter(prefix="/s")


async def _share(conn: asyncpg.Connection, token: str) -> asyncpg.Record:
    share = await sharing.link_share(conn, token)
    if not share:
        raise ApiError(404, "share.not_found")
    return share


@router.get("/{token}")
async def open_link(token: str, conn: asyncpg.Connection = Depends(get_conn)):
    share = await _share(conn, token)
    shared_by = await conn.fetchval("SELECT display_name FROM users WHERE id = $1", share["created_by"])
    if share["scope"] == "item":
        if not await sharing.link_covers(conn, share, share["entity_type"], share["entity_id"]):
            raise ApiError(404, "share.not_found")
        return {**await shared_payload(conn, share["entity_type"], share["entity_id"]), "type": share["entity_type"],
                "shared_by_name": shared_by, "expires_at": share["expires_at"]}
    table = sharing.TABLES[share["entity_type"]]
    items = await conn.fetch(f"SELECT id, title FROM {table} WHERE space_id = $1 AND deleted_at IS NULL ORDER BY created_at DESC", share["space_id"])
    return {"type": "section", "entity_type": share["entity_type"], "space_name": share["space_name"], "shared_by_name": shared_by,
            "expires_at": share["expires_at"], "items": [dict(i) for i in items]}


@router.get("/{token}/{entity_type}/{entity_id}")
async def open_item(token: str, entity_type: EntityType, entity_id: int, conn: asyncpg.Connection = Depends(get_conn)):
    share = await _share(conn, token)
    if not await sharing.link_covers(conn, share, entity_type, entity_id):
        raise ApiError(404, "share.not_found")
    return {**await shared_payload(conn, entity_type, entity_id), "type": entity_type}


@router.get("/{token}/media/{media_id}/{variant}")
async def link_media(token: str, media_id: int, variant: str, request: Request, conn: asyncpg.Connection = Depends(get_conn)):
    share = await _share(conn, token)
    if variant not in ("display", "thumb", "mp4", "poster") or not await sharing.link_can_see_media(conn, share, media_id):
        raise ApiError(404, "media.not_found")
    row = await conn.fetchrow(DERIVATIVE_SQL, media_id, variant)
    if not row:
        raise ApiError(404, "media.not_found")
    return await respond(conn, request, row)
