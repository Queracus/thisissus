from typing import Literal

import asyncpg
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, model_validator

from app import sharing
from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError
from app.policy import require_member
from app.routers.photos import gallery
from app.routers.tags import tags_json

router = APIRouter()
EntityType = Literal["date", "idea", "recipe"]


class ShareIn(BaseModel):
    scope: Literal["item", "section"]
    entity_type: EntityType
    entity_id: int | None = None
    target_user_id: int

    @model_validator(mode="after")
    def item_needs_id(self):
        if (self.scope == "item") != (self.entity_id is not None):
            raise ValueError("entity_id is required for item shares only")
        return self


async def _share_space(conn: asyncpg.Connection, request: Request, body_scope: str, entity_type: str, entity_id: int | None) -> int:
    if body_scope == "item":
        space_id = await sharing.entity_space(conn, entity_type, entity_id)
        if space_id is None:
            raise ApiError(404, "share.not_found")
        return space_id
    raw = request.headers.get("x-space-id")
    if not raw or not raw.isdigit():
        raise ApiError(400, "space.required")
    return int(raw)


@router.post("/shares")
async def create_share(body: ShareIn, request: Request, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    space_id = await _share_space(conn, request, body.scope, body.entity_type, body.entity_id)
    await require_member(conn, user["id"], space_id, "write")
    if body.target_user_id not in {c["id"] for c in await sharing.contacts(conn, user["id"])}:
        raise ApiError(400, "share.not_a_contact")
    existing = await conn.fetchval(
        f"""SELECT id FROM shares s WHERE {sharing.LIVE} AND space_id = $1 AND scope = $2 AND entity_type = $3
            AND entity_id IS NOT DISTINCT FROM $4 AND target_user_id = $5""",
        space_id, body.scope, body.entity_type, body.entity_id, body.target_user_id)
    share_id = existing or await conn.fetchval(
        """INSERT INTO shares (space_id, created_by, scope, entity_type, entity_id, target_user_id)
           VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
        space_id, user["id"], body.scope, body.entity_type, body.entity_id, body.target_user_id)
    return {"id": share_id}


SHARE_ROWS = f"""SELECT s.id, s.scope, s.entity_type, s.entity_id, s.created_at, s.expires_at, s.token_hash IS NOT NULL AS is_link,
                        t.display_name AS target_name, c.display_name AS created_by_name
                 FROM shares s LEFT JOIN users t ON t.id = s.target_user_id LEFT JOIN users c ON c.id = s.created_by
                 WHERE {sharing.LIVE}"""


@router.get("/shares")
async def list_shares(request: Request, entity_type: EntityType | None = None, entity_id: int | None = None,
                      user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    """With entity_type+entity_id: who can see this item (badges). Without: every active share of the active space."""
    if entity_type and entity_id:
        space_id = await sharing.entity_space(conn, entity_type, entity_id)
        if space_id is None:
            raise ApiError(404, "share.not_found")
        await require_member(conn, user["id"], space_id)
        rows = await conn.fetch(f"""{SHARE_ROWS} AND s.space_id = $1 AND s.entity_type = $2
                                    AND (s.scope = 'section' OR s.entity_id = $3) ORDER BY s.id""", space_id, entity_type, entity_id)
    else:
        raw = request.headers.get("x-space-id")
        if not raw or not raw.isdigit():
            raise ApiError(400, "space.required")
        await require_member(conn, user["id"], int(raw))
        rows = await conn.fetch(f"{SHARE_ROWS} AND s.space_id = $1 ORDER BY s.id DESC", int(raw))
    return [dict(r) for r in rows]


@router.delete("/shares/{share_id}")
async def revoke_share(share_id: int, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    """Any member of the space can revoke (so neither partner shares joint memories behind the other's back)."""
    space_id = await conn.fetchval("SELECT space_id FROM shares WHERE id = $1 AND revoked_at IS NULL", share_id)
    if space_id is None:
        raise ApiError(404, "share.not_found")
    await require_member(conn, user["id"], space_id, "write")
    await conn.execute("UPDATE shares SET revoked_at = now() WHERE id = $1", share_id)
    return {"ok": True}


@router.get("/shares/contacts")
async def contacts(user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await sharing.contacts(conn, user["id"])


@router.get("/shared-with-me")
async def shared_with_me(user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await sharing.shared_with(conn, user["id"])


async def shared_payload(conn: asyncpg.Connection, entity_type: str, entity_id: int) -> dict:
    """What a viewer of a share sees: no personal reviews/notes, no exact coordinates, photos as derivatives only."""
    if entity_type == "date":
        row = await conn.fetchrow(
            f"""SELECT id, title, starts_at, ends_at, place_name, {tags_json('date_tags', 'date_id', 'dates.id')} AS tags,
                       (SELECT avg(rating)::float FROM date_reviews WHERE date_id = dates.id) AS avg_rating
                FROM dates WHERE id = $1""", entity_id)
        return {**dict(row), "photos": await gallery(conn, "date_media", "date_id", entity_id)}
    if entity_type == "recipe":
        row = await conn.fetchrow(
            f"""SELECT id, title, portions, prep_minutes, source_url, {tags_json('recipe_tags', 'recipe_id', 'recipes.id')} AS tags,
                       (SELECT avg(rating)::float FROM recipe_reviews WHERE recipe_id = recipes.id) AS avg_rating
                FROM recipes WHERE id = $1""", entity_id)
        ingredients = await conn.fetch("SELECT amount::float AS amount, unit, item FROM recipe_ingredients WHERE recipe_id = $1 ORDER BY position", entity_id)
        steps = await conn.fetch("SELECT text FROM recipe_steps WHERE recipe_id = $1 ORDER BY position", entity_id)
        return {**dict(row), "ingredients": [dict(i) for i in ingredients], "steps": [s["text"] for s in steps],
                "photos": await gallery(conn, "recipe_media", "recipe_id", entity_id)}
    row = await conn.fetchrow(
        f"""SELECT id, title, description, url, est_cost::float AS est_cost, season, status, scheduled_at,
                   {tags_json('idea_tags', 'idea_id', 'ideas.id')} AS tags FROM ideas WHERE id = $1""", entity_id)
    return dict(row)


@router.get("/shared/{entity_type}/{entity_id}")
async def shared_item(entity_type: EntityType, entity_id: int, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    grant = await sharing.user_grant(conn, user["id"], entity_type, entity_id)
    if not grant:
        raise ApiError(404, "share.not_found")
    shared_by = await conn.fetchval("SELECT display_name FROM users WHERE id = $1", grant["created_by"])
    return {**await shared_payload(conn, entity_type, entity_id), "type": entity_type, "shared_by_name": shared_by}
