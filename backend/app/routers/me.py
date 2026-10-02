import asyncpg
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth.deps import current_user
from app.auth.pin import set_pin
from app.auth.sessions import COOKIE
from app.auth.tokens import hash_token
from app.db import get_conn
from app.errors import ApiError

router = APIRouter(prefix="/me")


class PinIn(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9._-]{3,30}$")
    pin: str = Field(pattern=r"^\d{6}$")


@router.put("/pin")
async def put_pin(body: PinIn, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await set_pin(conn, user["id"], body.username, body.pin)
    return {"ok": True}


@router.get("/sessions")
async def list_sessions(request: Request, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    rows = await conn.fetch(
        """SELECT id, user_agent, created_at, last_seen_at, token_hash = $2 AS current
           FROM sessions WHERE user_id = $1 AND expires_at > now() ORDER BY last_seen_at DESC""",
        user["id"], hash_token(request.cookies.get(COOKIE, "")))
    return [dict(r) for r in rows]


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    if await conn.execute("DELETE FROM sessions WHERE id = $1 AND user_id = $2", session_id, user["id"]) == "DELETE 0":
        raise ApiError(404, "not_found")
    return {"ok": True}


@router.post("/sessions/revoke-others")
async def revoke_other_sessions(request: Request, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await conn.execute("DELETE FROM sessions WHERE user_id = $1 AND token_hash <> $2", user["id"], hash_token(request.cookies.get(COOKIE, "")))
    return {"ok": True}
