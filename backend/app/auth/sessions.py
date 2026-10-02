from datetime import timedelta

import asyncpg
from fastapi import Response

from app import config
from app.auth.tokens import hash_token, new_token

COOKIE = "sid"
SESSION_TTL = timedelta(days=60)  # sliding: every request extends it


async def create_session(conn: asyncpg.Connection, user_id: int, user_agent: str | None) -> str:
    raw, h = new_token()
    await conn.execute("INSERT INTO sessions (token_hash, user_id, expires_at, user_agent) VALUES ($1, $2, now() + $3, $4)", h, user_id, SESSION_TTL, user_agent)
    return raw


async def touch_session(conn: asyncpg.Connection, raw: str) -> asyncpg.Record | None:
    """Extend a live session and return its (enabled) user, else None."""
    return await conn.fetchrow(
        """WITH s AS (UPDATE sessions SET last_seen_at = now(), expires_at = now() + $2
                      WHERE token_hash = $1 AND expires_at > now() RETURNING user_id)
           SELECT u.* FROM users u JOIN s ON s.user_id = u.id WHERE u.disabled_at IS NULL""",
        hash_token(raw), SESSION_TTL)


async def delete_session(conn: asyncpg.Connection, raw: str) -> None:
    await conn.execute("DELETE FROM sessions WHERE token_hash = $1", hash_token(raw))


def set_session_cookie(response: Response, raw: str) -> None:
    response.set_cookie(COOKIE, raw, max_age=int(SESSION_TTL.total_seconds()), httponly=True, samesite="lax", secure=config.COOKIE_SECURE, path="/")
