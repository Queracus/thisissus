"""Chunked media storage in Postgres. Uploads stream in 1 MB pieces; reads fetch only the chunks a range needs."""
import hashlib

import asyncpg
from fastapi import UploadFile

from app.errors import ApiError

CHUNK_SIZE = 1024 * 1024
PHOTO_MAX_BYTES = 25 * 1024 * 1024
VIDEO_MAX_BYTES = 50 * 1024 * 1024
HEIF_BRANDS = {b"heic", b"heix", b"heim", b"heis", b"hevc", b"mif1", b"msf1"}
VIDEO_BRANDS = {b"qt  ", b"isom", b"iso2", b"mp41", b"mp42", b"avc1", b"M4V "}


def sniff(head: bytes) -> str | None:
    """Real file type from magic bytes (the browser's Content-Type is not trusted)."""
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in HEIF_BRANDS:
            return "image/heic"
        if brand in VIDEO_BRANDS:
            return "video/quicktime" if brand == b"qt  " else "video/mp4"
    return None


async def _new_media(conn, space_id, user_id, kind, variant, mime, parent_id=None, status="ready") -> int:
    return await conn.fetchval(
        """INSERT INTO media (space_id, created_by, kind, variant, mime, chunk_size, parent_id, status)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id""",
        space_id, user_id, kind, variant, mime, CHUNK_SIZE, parent_id, status)


async def _finish(conn, media_id: int, size: int, digest: bytes) -> None:
    await conn.execute("UPDATE media SET size = $2, sha256 = $3 WHERE id = $1", media_id, size, digest)


async def save_upload(conn: asyncpg.Connection, space_id: int, user_id: int, file: UploadFile,
                      allowed: dict[str, str]) -> tuple[int, str]:
    """Stream an upload into chunks. `allowed` maps sniffed mime → kind (photo|video). Returns (media_id, kind).
    Call inside a transaction: a rejected upload rolls back every chunk written so far."""
    first = await file.read(CHUNK_SIZE)
    mime = sniff(first[:16])
    if mime not in allowed:
        raise ApiError(415, "media.unsupported_type")
    kind = allowed[mime]
    max_bytes = VIDEO_MAX_BYTES if kind == "video" else PHOTO_MAX_BYTES
    media_id = await _new_media(conn, space_id, user_id, kind, "original", mime, status="pending")
    sha, size, seq, chunk = hashlib.sha256(), 0, 0, first
    while chunk:
        size += len(chunk)
        if size > max_bytes:
            raise ApiError(413, "media.too_large")
        sha.update(chunk)
        await conn.execute("INSERT INTO media_chunks (media_id, seq, data) VALUES ($1, $2, $3)", media_id, seq, chunk)
        seq, chunk = seq + 1, await file.read(CHUNK_SIZE)
    await _finish(conn, media_id, size, sha.digest())
    return media_id, kind


async def save_bytes(conn: asyncpg.Connection, space_id: int, user_id: int | None, kind: str, variant: str, mime: str,
                     data: bytes, parent_id: int | None = None) -> int:
    """Store in-memory bytes (derivatives)."""
    media_id = await _new_media(conn, space_id, user_id, kind, variant, mime, parent_id)
    await conn.executemany("INSERT INTO media_chunks (media_id, seq, data) VALUES ($1, $2, $3)",
                           [(media_id, i, data[off:off + CHUNK_SIZE]) for i, off in enumerate(range(0, len(data), CHUNK_SIZE))])
    await _finish(conn, media_id, len(data), hashlib.sha256(data).digest())
    return media_id


async def read_range(conn: asyncpg.Connection, media_id: int, start: int, end: int) -> bytes:
    """Bytes start..end (inclusive), reading only the chunks that overlap."""
    chunk_size = await conn.fetchval("SELECT chunk_size FROM media WHERE id = $1", media_id)
    first, last = start // chunk_size, end // chunk_size
    rows = await conn.fetch("SELECT data FROM media_chunks WHERE media_id = $1 AND seq BETWEEN $2 AND $3 ORDER BY seq", media_id, first, last)
    blob = b"".join(r["data"] for r in rows)
    offset = start - first * chunk_size
    return blob[offset:offset + end - start + 1]


async def read_all(conn: asyncpg.Connection, media_id: int) -> bytes:
    rows = await conn.fetch("SELECT data FROM media_chunks WHERE media_id = $1 ORDER BY seq", media_id)
    return b"".join(r["data"] for r in rows)
