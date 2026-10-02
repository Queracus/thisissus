from datetime import datetime
from typing import Literal

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, HttpUrl

from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError
from app.notify import notify_space
from app.policy import active_space, scope_sql
from app.routers.dates import TagOut
from app.routers.photos import gallery, gallery_router
from app.routers.tags import set_tags, tags_json

router = APIRouter(prefix="/recipes")
COLUMNS = """r.id, r.space_id, r.title, r.portions, r.prep_minutes, r.source_url, r.status, r.created_by, r.created_at,
             """ + tags_json("recipe_tags", "recipe_id", "r.id") + """ AS tags,
             (SELECT m.id FROM recipe_media j JOIN media m ON m.id = j.media_id
              WHERE j.recipe_id = r.id AND m.status = 'ready' AND m.deleted_at IS NULL ORDER BY j.position LIMIT 1) AS thumb_id,
             (SELECT avg(x.rating)::float FROM recipe_reviews x WHERE x.recipe_id = r.id) AS avg_rating"""


class IngredientIn(BaseModel):
    amount: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=20)
    item: str = Field(min_length=1, max_length=200)


class RecipeIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    portions: int = Field(default=2, ge=1, le=100)
    prep_minutes: int | None = Field(default=None, ge=0, le=10000)
    source_url: HttpUrl | None = None
    status: Literal["want", "cooked"] = "want"
    ingredients: list[IngredientIn] = Field(default=[], max_length=100)
    steps: list[str] = Field(default=[], max_length=100)
    tag_ids: list[int] = []


class IngredientOut(BaseModel):
    amount: float | None
    unit: str | None
    item: str


class RecipeOut(BaseModel):
    id: int
    space_id: int
    title: str
    portions: int
    prep_minutes: int | None
    source_url: str | None
    status: str
    created_by: int | None
    created_at: datetime
    tags: list[TagOut]
    thumb_id: int | None
    avg_rating: float | None
    ingredients: list[IngredientOut] = []
    steps: list[str] = []
    photos: list[dict] = []
    reviews: list[dict] = []
    cooks: list[dict] = []


class RecipeReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class CookedIn(BaseModel):
    log_as_date: bool = False


async def visible_recipe(conn: asyncpg.Connection, user_id: int, recipe_id: int) -> dict:
    scope, params = scope_sql(user_id, "r.space_id", 2)
    row = await conn.fetchrow(f"SELECT {COLUMNS} FROM recipes r WHERE r.id = $1 AND r.deleted_at IS NULL AND {scope}", recipe_id, *params)
    if not row:
        raise ApiError(404, "recipe.not_found")
    return dict(row)


async def full_recipe(conn: asyncpg.Connection, user_id: int, recipe_id: int) -> dict:
    recipe = await visible_recipe(conn, user_id, recipe_id)
    recipe["ingredients"] = [dict(r) for r in await conn.fetch(
        "SELECT amount::float AS amount, unit, item FROM recipe_ingredients WHERE recipe_id = $1 ORDER BY position", recipe_id)]
    recipe["steps"] = [r["text"] for r in await conn.fetch("SELECT text FROM recipe_steps WHERE recipe_id = $1 ORDER BY position", recipe_id)]
    recipe["photos"] = await gallery(conn, "recipe_media", "recipe_id", recipe_id)
    recipe["reviews"] = [dict(r) for r in await conn.fetch(
        """SELECT x.user_id, u.display_name, x.rating, x.comment FROM recipe_reviews x JOIN users u ON u.id = x.user_id
           WHERE x.recipe_id = $1 ORDER BY x.updated_at""", recipe_id)]
    recipe["cooks"] = [dict(r) for r in await conn.fetch(
        """SELECT c.id, c.created_at, c.date_id, u.display_name AS cooked_by FROM recipe_cooks c LEFT JOIN users u ON u.id = c.created_by
           WHERE c.recipe_id = $1 ORDER BY c.created_at DESC""", recipe_id)]
    return recipe


async def save_parts(conn: asyncpg.Connection, recipe_id: int, space_id: int, body: RecipeIn) -> None:
    """Ingredients, steps and tags are replaced as a whole on every save."""
    await conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = $1", recipe_id)
    await conn.executemany("INSERT INTO recipe_ingredients (recipe_id, position, amount, unit, item) VALUES ($1, $2, $3, $4, $5)",
                           [(recipe_id, i, x.amount, x.unit, x.item) for i, x in enumerate(body.ingredients)])
    await conn.execute("DELETE FROM recipe_steps WHERE recipe_id = $1", recipe_id)
    await conn.executemany("INSERT INTO recipe_steps (recipe_id, position, text) VALUES ($1, $2, $3)",
                           [(recipe_id, i, s) for i, s in enumerate(s.strip() for s in body.steps) if s])
    await set_tags(conn, "recipe_tags", "recipe_id", recipe_id, space_id, body.tag_ids)


@router.get("", response_model=list[RecipeOut])
async def list_recipes(space=Depends(active_space), conn: asyncpg.Connection = Depends(get_conn),
                       status: Literal["want", "cooked"] | None = None):
    rows = await conn.fetch(
        f"""SELECT {COLUMNS} FROM recipes r WHERE r.space_id = $1 AND r.deleted_at IS NULL AND ($2::text IS NULL OR r.status = $2)
            ORDER BY r.created_at DESC, r.id DESC""", space["id"], status)
    return [dict(r) for r in rows]


@router.post("", response_model=RecipeOut)
async def create_recipe(body: RecipeIn, space=Depends(active_space), user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    async with conn.transaction():
        recipe_id = await conn.fetchval(
            """INSERT INTO recipes (space_id, title, portions, prep_minutes, source_url, status, created_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
            space["id"], body.title, body.portions, body.prep_minutes, body.source_url and str(body.source_url), body.status, user["id"])
        await save_parts(conn, recipe_id, space["id"], body)
        await notify_space(conn, user["id"], space["id"], "recipe.created", {"recipe_id": recipe_id, "title": body.title})
    return await full_recipe(conn, user["id"], recipe_id)


@router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe(recipe_id: int, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await full_recipe(conn, user["id"], recipe_id)


@router.put("/{recipe_id}", response_model=RecipeOut)
async def update_recipe(recipe_id: int, body: RecipeIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    recipe = await visible_recipe(conn, user["id"], recipe_id)
    async with conn.transaction():
        await conn.execute(
            """UPDATE recipes SET title = $2, portions = $3, prep_minutes = $4, source_url = $5, status = $6, updated_at = now() WHERE id = $1""",
            recipe_id, body.title, body.portions, body.prep_minutes, body.source_url and str(body.source_url), body.status)
        await save_parts(conn, recipe_id, recipe["space_id"], body)
    return await full_recipe(conn, user["id"], recipe_id)


@router.delete("/{recipe_id}")
async def delete_recipe(recipe_id: int, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await visible_recipe(conn, user["id"], recipe_id)
    await conn.execute("UPDATE recipes SET deleted_at = now() WHERE id = $1", recipe_id)
    return {"ok": True}


@router.put("/{recipe_id}/review")
async def put_review(recipe_id: int, body: RecipeReviewIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    """Create or replace the caller's own review."""
    await visible_recipe(conn, user["id"], recipe_id)
    await conn.execute(
        """INSERT INTO recipe_reviews (recipe_id, user_id, rating, comment) VALUES ($1, $2, $3, $4)
           ON CONFLICT (recipe_id, user_id) DO UPDATE SET rating = $3, comment = $4, updated_at = now()""",
        recipe_id, user["id"], body.rating, body.comment)
    return {"ok": True}


@router.post("/{recipe_id}/cooked")
async def cooked(recipe_id: int, body: CookedIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    """"We cooked it": log the cook, mark as cooked, optionally record it as a Date We've Had, tell the others to rate it."""
    recipe = await visible_recipe(conn, user["id"], recipe_id)
    async with conn.transaction():
        date_id = None
        if body.log_as_date:
            date_id = await conn.fetchval(
                "INSERT INTO dates (space_id, title, starts_at, created_by, recipe_id) VALUES ($1, $2, now(), $3, $4) RETURNING id",
                recipe["space_id"], recipe["title"], user["id"], recipe_id)
            await conn.execute("INSERT INTO date_tags (date_id, tag_id) SELECT $1, tag_id FROM recipe_tags WHERE recipe_id = $2", date_id, recipe_id)
        await conn.execute("INSERT INTO recipe_cooks (recipe_id, date_id, created_by) VALUES ($1, $2, $3)", recipe_id, date_id, user["id"])
        await conn.execute("UPDATE recipes SET status = 'cooked', updated_at = now() WHERE id = $1", recipe_id)
        await notify_space(conn, user["id"], recipe["space_id"], "recipe.cooked",
                           {"recipe_id": recipe_id, "title": recipe["title"], "date_id": date_id})
    return {"recipe": await full_recipe(conn, user["id"], recipe_id), "date_id": date_id}


photo_router = gallery_router("/recipes", "recipe_media", "recipe_id", visible_recipe)
