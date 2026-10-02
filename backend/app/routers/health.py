import asyncpg
from fastapi import APIRouter, Depends

from app.db import get_conn

router = APIRouter()


@router.get("/health")
async def health(conn: asyncpg.Connection = Depends(get_conn)):
    return {"ok": True, "db": await conn.fetchval("SELECT 1") == 1}
