from datetime import datetime
from typing import Literal

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, HttpUrl

from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError
from app.policy import active_space, scope_sql
from app.routers.dates import TagOut
from app.routers.tags import set_tags, tags_json

router = APIRouter(prefix="/ideas")

# Invitees: explicit rows in idea_invitees, or (none) every other member of the space. The suggester always takes part.
INVITEE_IDS = """SELECT m.user_id FROM space_members m
                 WHERE m.space_id = {i}.space_id AND m.user_id IS DISTINCT FROM {i}.suggested_by
                   AND (NOT EXISTS (SELECT 1 FROM idea_invitees x WHERE x.idea_id = {i}.id)
                        OR m.user_id IN (SELECT x.user_id FROM idea_invitees x WHERE x.idea_id = {i}.id))"""
COLUMNS = """i.id, i.space_id, i.title, i.description, i.url, i.est_cost::float AS est_cost, i.season, i.status, i.scheduled_at,
             i.times_done, i.suggested_by, u.display_name AS suggested_by_name, i.created_at,
             """ + tags_json("idea_tags", "idea_id", "i.id") + """ AS tags,
             (SELECT coalesce(json_agg(json_build_object('id', iu.id, 'display_name', iu.display_name) ORDER BY iu.display_name), '[]')
              FROM users iu WHERE iu.id IN (""" + INVITEE_IDS.format(i="i") + """)) AS invitees,
             (SELECT array_agg(x.user_id ORDER BY x.user_id) FROM idea_invitees x WHERE x.idea_id = i.id) AS invitee_ids"""
FROM = "ideas i LEFT JOIN users u ON u.id = i.suggested_by"


class IdeaIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    url: HttpUrl | None = None  # http(s) only: no javascript: links
    est_cost: float | None = Field(default=None, ge=0)
    season: Literal["spring", "summer", "autumn", "winter"] | None = None
    tag_ids: list[int] = []
    invitee_ids: list[int] | None = None  # None = everyone in the space


class PersonOut(BaseModel):
    id: int
    display_name: str


class IdeaOut(BaseModel):
    id: int
    space_id: int
    title: str
    description: str | None
    url: str | None
    est_cost: float | None
    season: str | None
    status: str
    scheduled_at: datetime | None
    times_done: int
    suggested_by: int | None
    suggested_by_name: str | None
    created_at: datetime
    tags: list[TagOut]
    invitees: list[PersonOut]
    invitee_ids: list[int] | None  # explicit choice; None = everyone


async def visible_idea(conn: asyncpg.Connection, user_id: int, idea_id: int) -> dict:
    scope, params = scope_sql(user_id, "i.space_id", 2)
    row = await conn.fetchrow(f"SELECT {COLUMNS} FROM {FROM} WHERE i.id = $1 AND i.deleted_at IS NULL AND {scope}", idea_id, *params)
    if not row:
        raise ApiError(404, "idea.not_found")
    return dict(row)


async def set_invitees(conn: asyncpg.Connection, idea_id: int, space_id: int, invitee_ids: list[int] | None) -> None:
    """None = everyone (no rows). Invitees must be members of the idea's space."""
    await conn.execute("DELETE FROM idea_invitees WHERE idea_id = $1", idea_id)
    if invitee_ids is None:
        return
    ids = sorted(set(invitee_ids))
    if await conn.fetchval("SELECT count(*) FROM space_members WHERE space_id = $1 AND user_id = ANY($2::bigint[])", space_id, ids) != len(ids):
        raise ApiError(400, "idea.invalid_invitee")
    await conn.executemany("INSERT INTO idea_invitees (idea_id, user_id) VALUES ($1, $2)", [(idea_id, u) for u in ids])


async def participants(conn: asyncpg.Connection, idea_id: int) -> frozenset[int]:
    """Suggester + invitees: the people the time negotiation waits for."""
    rows = await conn.fetch(f"SELECT i.suggested_by AS user_id FROM ideas i WHERE i.id = $1 AND i.suggested_by IS NOT NULL "
                            f"UNION SELECT q.user_id FROM ideas i, LATERAL ({INVITEE_IDS.format(i='i')}) q WHERE i.id = $1", idea_id)
    return frozenset(r["user_id"] for r in rows)


@router.get("", response_model=list[IdeaOut])
async def list_ideas(space: asyncpg.Record = Depends(active_space), conn: asyncpg.Connection = Depends(get_conn), archived: bool = False):
    """Open ideas by default; ?archived=true lists the ones someone passed on."""
    rows = await conn.fetch(
        f"""SELECT {COLUMNS} FROM {FROM} WHERE i.space_id = $1 AND i.deleted_at IS NULL AND (i.status = 'archived') = $2
            ORDER BY i.created_at DESC, i.id DESC""", space["id"], archived)
    return [dict(r) for r in rows]


@router.post("", response_model=IdeaOut)
async def create_idea(body: IdeaIn, space: asyncpg.Record = Depends(active_space), user: asyncpg.Record = Depends(current_user),
                      conn: asyncpg.Connection = Depends(get_conn)):
    async with conn.transaction():
        idea_id = await conn.fetchval(
            """INSERT INTO ideas (space_id, title, description, url, est_cost, season, suggested_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
            space["id"], body.title, body.description, body.url and str(body.url), body.est_cost, body.season, user["id"])
        await set_tags(conn, "idea_tags", "idea_id", idea_id, space["id"], body.tag_ids)
        await set_invitees(conn, idea_id, space["id"], body.invitee_ids)
    return await visible_idea(conn, user["id"], idea_id)


@router.get("/{idea_id}", response_model=IdeaOut)
async def get_idea(idea_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await visible_idea(conn, user["id"], idea_id)


@router.put("/{idea_id}", response_model=IdeaOut)
async def update_idea(idea_id: int, body: IdeaIn, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    idea = await visible_idea(conn, user["id"], idea_id)
    async with conn.transaction():
        await conn.execute(
            """UPDATE ideas SET title = $2, description = $3, url = $4, est_cost = $5, season = $6, updated_at = now() WHERE id = $1""",
            idea_id, body.title, body.description, body.url and str(body.url), body.est_cost, body.season)
        await set_tags(conn, "idea_tags", "idea_id", idea_id, idea["space_id"], body.tag_ids)
        await set_invitees(conn, idea_id, idea["space_id"], body.invitee_ids)
    return await visible_idea(conn, user["id"], idea_id)


@router.delete("/{idea_id}")
async def delete_idea(idea_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await visible_idea(conn, user["id"], idea_id)
    await conn.execute("UPDATE ideas SET deleted_at = now() WHERE id = $1", idea_id)
    return {"ok": True}
