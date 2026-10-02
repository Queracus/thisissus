import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.db import get_conn
from app.errors import ApiError
from app.policy import active_space

router = APIRouter(prefix="/tags")


class TagIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)


@router.get("")
async def list_tags(space: asyncpg.Record = Depends(active_space), conn: asyncpg.Connection = Depends(get_conn)):
    rows = await conn.fetch("SELECT id, name, starter_key FROM tags WHERE space_id = $1 ORDER BY starter_key IS NULL, lower(name)", space["id"])
    return [dict(r) for r in rows]


@router.post("")
async def create_tag(body: TagIn, space: asyncpg.Record = Depends(active_space), conn: asyncpg.Connection = Depends(get_conn)):
    """Idempotent: an existing tag with the same name (any case) is returned instead of a duplicate."""
    name = body.name.strip()
    row = await conn.fetchrow(
        """WITH ins AS (INSERT INTO tags (space_id, name) VALUES ($1, $2) ON CONFLICT DO NOTHING RETURNING id, name, starter_key)
           SELECT * FROM ins UNION ALL SELECT id, name, starter_key FROM tags WHERE space_id = $1 AND lower(name) = lower($2) LIMIT 1""",
        space["id"], name)
    return dict(row)


async def set_tags(conn: asyncpg.Connection, join_table: str, fk: str, item_id: int, space_id: int, tag_ids: list[int]) -> None:
    """Replace an item's tags; every tag must belong to the item's space (400 tag.invalid)."""
    tag_ids = sorted(set(tag_ids))
    if tag_ids and await conn.fetchval("SELECT count(*) FROM tags WHERE id = ANY($1::bigint[]) AND space_id = $2", tag_ids, space_id) != len(tag_ids):
        raise ApiError(400, "tag.invalid")
    await conn.execute(f"DELETE FROM {join_table} WHERE {fk} = $1", item_id)
    await conn.executemany(f"INSERT INTO {join_table} ({fk}, tag_id) VALUES ($1, $2)", [(item_id, t) for t in tag_ids])


def tags_json(join_table: str, fk: str, item_col: str) -> str:
    """SQL expression: the item's tags as a JSON array (for list/detail queries)."""
    return f"""(SELECT coalesce(json_agg(json_build_object('id', t.id, 'name', t.name, 'starter_key', t.starter_key) ORDER BY t.id), '[]')
               FROM {join_table} jt JOIN tags t ON t.id = jt.tag_id WHERE jt.{fk} = {item_col})"""
