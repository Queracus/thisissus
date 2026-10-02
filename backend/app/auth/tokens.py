import hashlib
import secrets
from datetime import timedelta

import asyncpg

from app.errors import ApiError


def hash_token(raw: str) -> bytes:
    return hashlib.sha256(raw.encode()).digest()


def new_token() -> tuple[str, bytes]:
    """Random URL-safe token and its sha256 (only the hash is stored)."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


async def issue_token(conn: asyncpg.Connection, kind: str, user_id: int, ttl: timedelta) -> str:
    raw, h = new_token()
    await conn.execute("INSERT INTO auth_tokens (token_hash, kind, user_id, expires_at) VALUES ($1, $2, $3, now() + $4)", h, kind, user_id, ttl)
    return raw


async def invite_new_user(conn: asyncpg.Connection, display_name: str, ttl: timedelta = timedelta(days=7)) -> str:
    """Create a user without a passkey yet and return their one-time invite token."""
    user_id = await conn.fetchval("INSERT INTO users (display_name) VALUES ($1) RETURNING id", display_name)
    return await issue_token(conn, "invite", user_id, ttl)


async def valid_token(conn: asyncpg.Connection, raw: str, kinds: tuple[str, ...] = ("invite",)) -> asyncpg.Record:
    row = await conn.fetchrow(
        "SELECT * FROM auth_tokens WHERE token_hash = $1 AND kind = ANY($2::text[]) AND used_at IS NULL AND expires_at > now()",
        hash_token(raw), list(kinds))
    if not row:
        raise ApiError(400, "auth.invalid_token")
    return row


async def use_token(conn: asyncpg.Connection, raw: str) -> None:
    await conn.execute("UPDATE auth_tokens SET used_at = now() WHERE token_hash = $1", hash_token(raw))
