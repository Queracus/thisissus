from datetime import timedelta

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app import config
from app.auth.deps import current_user
from app.auth.tokens import invite_new_user, issue_token, use_token, valid_token
from app.db import get_conn
from app.policy import active_space, require_member, scope_sql

router = APIRouter()
INVITE_TTL = timedelta(days=7)


class NameIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class SpaceInviteIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=60)


class JoinIn(BaseModel):
    token: str


async def add_member(conn: asyncpg.Connection, space_id: int, user_id: int, role: str = "member") -> None:
    await conn.execute("INSERT INTO space_members (space_id, user_id, role) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING", space_id, user_id, role)


@router.get("/spaces")
async def my_spaces(user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    scope, params = scope_sql(user["id"], "s.id", 1)
    rows = await conn.fetch(
        f"""SELECT s.id, s.name, m.role FROM spaces s JOIN space_members m ON m.space_id = s.id AND m.user_id = $1
            WHERE {scope} ORDER BY s.id""", *params)
    return [dict(r) for r in rows]


@router.get("/space")
async def current_space(space: asyncpg.Record = Depends(active_space)):
    return dict(space)


@router.patch("/spaces/{space_id}")
async def rename_space(space_id: int, body: NameIn, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await require_member(conn, user["id"], space_id, "manage")
    await conn.execute("UPDATE spaces SET name = $2 WHERE id = $1", space_id, body.name)
    return {"ok": True}


@router.get("/spaces/{space_id}/members")
async def members(space_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await require_member(conn, user["id"], space_id)
    rows = await conn.fetch(
        """SELECT u.id, u.display_name, m.role FROM space_members m JOIN users u ON u.id = m.user_id
           WHERE m.space_id = $1 ORDER BY m.role DESC, m.joined_at""", space_id)
    return [dict(r) for r in rows]


@router.post("/spaces/{space_id}/invites")
async def invite(space_id: int, body: SpaceInviteIn, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    """With display_name: new person (registers a passkey, then joins). Without: join link for an existing user."""
    await require_member(conn, user["id"], space_id, "manage")
    if body.display_name:
        return {"url": f"{config.ORIGIN}/invite/{await invite_new_user(conn, body.display_name, space_id=space_id)}"}
    return {"url": f"{config.ORIGIN}/join/{await issue_token(conn, 'space_invite', None, INVITE_TTL, space_id=space_id)}"}


@router.post("/spaces/join")
async def join(body: JoinIn, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    tok = await valid_token(conn, body.token, ("space_invite",))
    async with conn.transaction():
        await add_member(conn, tok["space_id"], user["id"])
        await use_token(conn, body.token)
    return {"space_id": tok["space_id"]}
