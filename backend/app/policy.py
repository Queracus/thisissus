"""Access policy: the ONE place that decides who may see or change what. Routers never write their own visibility SQL.

Today: space membership (owner/member). Item and section shares extend scope_sql/can in #30/#31.
"""
import asyncpg
from fastapi import Depends, Header

from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError


async def space_role(conn: asyncpg.Connection, user_id: int, space_id: int) -> str | None:
    return await conn.fetchval("SELECT role FROM space_members WHERE space_id = $1 AND user_id = $2", space_id, user_id)


async def can(conn: asyncpg.Connection, user_id: int, action: str, space_id: int) -> bool:
    """read/write: any member; manage: owner only."""
    role = await space_role(conn, user_id, space_id)
    return role == "owner" if action == "manage" else role is not None


async def require_member(conn: asyncpg.Connection, user_id: int, space_id: int, action: str = "read") -> None:
    """404 for non-members (never reveal that a space exists), 403 for members lacking the right."""
    if await space_role(conn, user_id, space_id) is None:
        raise ApiError(404, "space.not_found")
    if not await can(conn, user_id, action, space_id):
        raise ApiError(403, "space.owner_required")


def scope_sql(user_id: int, space_col: str, param_index: int) -> tuple[str, list]:
    """WHERE fragment limiting rows to spaces the user belongs to, e.g. scope_sql(uid, "d.space_id", 2)."""
    return f"{space_col} IN (SELECT space_id FROM space_members WHERE user_id = ${param_index})", [user_id]


async def active_space(x_space_id: int = Header(), user: asyncpg.Record = Depends(current_user),
                       conn: asyncpg.Connection = Depends(get_conn)) -> asyncpg.Record:
    """Dependency for content endpoints: the space chosen in the X-Space-Id header, if the user is a member."""
    row = await conn.fetchrow(
        "SELECT s.id, s.name, m.role FROM spaces s JOIN space_members m ON m.space_id = s.id WHERE s.id = $1 AND m.user_id = $2",
        x_space_id, user["id"])
    if not row:
        raise ApiError(404, "space.not_found")
    return row
