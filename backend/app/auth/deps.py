import asyncpg
from fastapi import Depends, Request

from app.auth.sessions import COOKIE, touch_session
from app.db import get_conn
from app.errors import ApiError


async def current_user(request: Request, conn: asyncpg.Connection = Depends(get_conn)) -> asyncpg.Record:
    raw = request.cookies.get(COOKIE)
    user = raw and await touch_session(conn, raw)
    if not user:
        raise ApiError(401, "auth.required")
    return user
