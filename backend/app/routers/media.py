import re

import asyncpg
from fastapi import APIRouter, Depends, Request, Response

from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError
from app.media.store import read_range
from app.policy import scope_sql

router = APIRouter(prefix="/media")
VARIANTS = {"original", "display", "thumb", "mp4", "poster"}
CACHE = "private, max-age=31536000, immutable"  # a media id's bytes never change


def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """'bytes=a-b' | 'bytes=a-' | 'bytes=-n' → inclusive (start, end); None = whole file."""
    m = re.fullmatch(r"bytes=(\d*)-(\d*)", header or "")
    if not m or m.groups() == ("", ""):
        return None
    a, b = m.groups()
    start, end = (size - int(b), size - 1) if a == "" else (int(a), min(int(b), size - 1) if b else size - 1)
    if start < 0 or start > end:
        raise ApiError(416, "media.bad_range")
    return start, end


@router.get("/{media_id}/{variant}")
async def get_media(media_id: int, variant: str, request: Request, user: asyncpg.Record = Depends(current_user),
                    conn: asyncpg.Connection = Depends(get_conn)):
    if variant not in VARIANTS:
        raise ApiError(404, "media.not_found")
    scope, params = scope_sql(user["id"], "o.space_id", 3)
    row = await conn.fetchrow(
        f"""SELECT m.id, m.mime, m.size, encode(m.sha256, 'hex') AS etag FROM media o
            JOIN media m ON (m.id = o.id AND $2 = 'original') OR (m.parent_id = o.id AND m.variant = $2 AND m.status = 'ready')
            WHERE o.id = $1 AND o.variant = 'original' AND o.deleted_at IS NULL AND {scope}""",
        media_id, variant, *params)
    if not row:
        raise ApiError(404, "media.not_found")
    headers = {"Accept-Ranges": "bytes", "Cache-Control": CACHE, "ETag": f'"{row["etag"]}"'}
    if request.headers.get("if-none-match") == headers["ETag"]:
        return Response(status_code=304, headers=headers)
    rng = parse_range(request.headers.get("range"), row["size"])
    start, end = rng or (0, row["size"] - 1)
    body = await read_range(conn, row["id"], start, end) if row["size"] else b""
    if rng:
        headers["Content-Range"] = f"bytes {start}-{end}/{row['size']}"
    return Response(body, status_code=206 if rng else 200, media_type=row["mime"], headers=headers)
