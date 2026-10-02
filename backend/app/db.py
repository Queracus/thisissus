import json

import asyncpg
from fastapi import Request


async def init_conn(conn: asyncpg.Connection) -> None:
    """Decode json/jsonb columns into Python objects (asyncpg returns strings by default)."""
    for typ in ("json", "jsonb"):
        await conn.set_type_codec(typ, encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def get_conn(request: Request):
    """One pooled connection per request."""
    async with request.app.state.pool.acquire() as conn:
        yield conn
