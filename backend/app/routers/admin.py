from datetime import timedelta

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app import config
from app.auth.pin import unlock
from app.auth.roles import require_permission
from app.auth.tokens import invite_new_user, issue_token
from app.db import get_conn
from app.errors import ApiError

router = APIRouter(prefix="/admin")


@router.get("/users")
async def list_users(_=Depends(require_permission("manage_users")), conn: asyncpg.Connection = Depends(get_conn)):
    rows = await conn.fetch(
        """SELECT u.id, u.display_name, u.username, u.created_at,
                  coalesce(array_agg(r.name ORDER BY r.name) FILTER (WHERE r.name IS NOT NULL), '{}') AS roles,
                  EXISTS (SELECT 1 FROM passkeys p WHERE p.user_id = u.id) AS has_passkey,
                  EXISTS (SELECT 1 FROM login_throttle t WHERE t.key = 'user:' || u.id AND t.locked_until > now()) AS locked
           FROM users u LEFT JOIN user_roles ur ON ur.user_id = u.id LEFT JOIN roles r ON r.id = ur.role_id
           GROUP BY u.id ORDER BY u.id""")
    return [dict(r) for r in rows]


class RolesIn(BaseModel):
    roles: list[str]


@router.put("/users/{user_id}/roles")
async def set_roles(user_id: int, body: RolesIn, _=Depends(require_permission("manage_roles")), conn: asyncpg.Connection = Depends(get_conn)):
    role_ids = await conn.fetch("SELECT id FROM roles WHERE name = ANY($1::text[])", body.roles)
    if len(role_ids) != len(set(body.roles)):
        raise ApiError(400, "admin.unknown_role")
    async with conn.transaction():
        await conn.execute("DELETE FROM user_roles WHERE user_id = $1", user_id)
        await conn.executemany("INSERT INTO user_roles (user_id, role_id) VALUES ($1, $2)", [(user_id, r["id"]) for r in role_ids])
        if not await conn.fetchval("SELECT count(*) FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE r.name = 'admin'"):
            raise ApiError(409, "admin.last_admin")
    return {"ok": True}


@router.get("/roles")
async def list_roles(_=Depends(require_permission("manage_roles")), conn: asyncpg.Connection = Depends(get_conn)):
    rows = await conn.fetch(
        """SELECT r.name, coalesce(array_agg(rp.permission ORDER BY rp.permission) FILTER (WHERE rp.permission IS NOT NULL), '{}') AS permissions
           FROM roles r LEFT JOIN role_permissions rp ON rp.role_id = r.id GROUP BY r.id ORDER BY r.name""")
    return [dict(r) for r in rows]


class InviteIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)


@router.post("/invites")
async def create_invite(body: InviteIn, _=Depends(require_permission("issue_tokens")), conn: asyncpg.Connection = Depends(get_conn)):
    return {"url": f"{config.ORIGIN}/invite/{await invite_new_user(conn, body.display_name)}"}


@router.post("/users/{user_id}/unlock")
async def unlock_user(user_id: int, _=Depends(require_permission("manage_users")), conn: asyncpg.Connection = Depends(get_conn)):
    await unlock(conn, user_id)
    return {"ok": True}


@router.post("/users/{user_id}/recovery-link")
async def recovery_link(user_id: int, _=Depends(require_permission("issue_tokens")), conn: asyncpg.Connection = Depends(get_conn)):
    if not await conn.fetchval("SELECT 1 FROM users WHERE id = $1", user_id):
        raise ApiError(404, "not_found")
    return {"url": f"{config.ORIGIN}/recover/{await issue_token(conn, 'recovery', user_id, timedelta(hours=24))}"}


class SpaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    owner_id: int


@router.post("/spaces")
async def create_space(body: SpaceIn, _=Depends(require_permission("manage_spaces")), conn: asyncpg.Connection = Depends(get_conn)):
    async with conn.transaction():
        space_id = await conn.fetchval("INSERT INTO spaces (name) VALUES ($1) RETURNING id", body.name)
        try:
            await conn.execute("INSERT INTO space_members (space_id, user_id, role) VALUES ($1, $2, 'owner')", space_id, body.owner_id)
        except asyncpg.ForeignKeyViolationError:
            raise ApiError(404, "not_found")
    return {"id": space_id}


@router.get("/spaces")
async def list_spaces(_=Depends(require_permission("manage_spaces")), conn: asyncpg.Connection = Depends(get_conn)):
    rows = await conn.fetch(
        """SELECT s.id, s.name, array_agg(u.display_name ORDER BY m.role DESC, m.joined_at) AS members
           FROM spaces s JOIN space_members m ON m.space_id = s.id JOIN users u ON u.id = m.user_id GROUP BY s.id ORDER BY s.id""")
    return [dict(r) for r in rows]
