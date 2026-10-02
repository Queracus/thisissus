import asyncpg
from fastapi import Depends

from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError


async def grant_role(conn: asyncpg.Connection, user_id: int, role: str) -> None:
    await conn.execute("INSERT INTO user_roles (user_id, role_id) SELECT $1, id FROM roles WHERE name = $2 ON CONFLICT DO NOTHING", user_id, role)


async def user_permissions(conn: asyncpg.Connection, user_id: int) -> list[str]:
    rows = await conn.fetch(
        """SELECT DISTINCT rp.permission FROM user_roles ur JOIN role_permissions rp ON rp.role_id = ur.role_id
           WHERE ur.user_id = $1 ORDER BY 1""", user_id)
    return [r["permission"] for r in rows]


def require_permission(permission: str):
    """Dependency: the current user, or 403 auth.forbidden if they lack the permission."""
    async def dep(user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)) -> asyncpg.Record:
        if permission not in await user_permissions(conn, user["id"]):
            raise ApiError(403, "auth.forbidden")
        return user
    return dep
