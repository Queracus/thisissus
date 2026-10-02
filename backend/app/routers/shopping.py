import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.db import get_conn
from app.errors import ApiError
from app.policy import active_space
from app.recipes_tools import scale

router = APIRouter(prefix="/shopping")
COLUMNS = "id, item, amount::float AS amount, unit, recipe_id, checked_at IS NOT NULL AS checked"


class ItemIn(BaseModel):
    item: str = Field(min_length=1, max_length=200)
    amount: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=20)


class CheckIn(BaseModel):
    checked: bool


class FromRecipeIn(BaseModel):
    recipe_id: int
    portions: int = Field(ge=1, le=100)


async def add_item(conn: asyncpg.Connection, space_id: int, item: str, amount, unit, recipe_id=None) -> int:
    """Merge into an unticked line with the same item + unit (amounts add up); otherwise a new line."""
    if amount is not None:
        merged = await conn.fetchval(
            """UPDATE shopping_items SET amount = amount + $4
               WHERE id = (SELECT id FROM shopping_items WHERE space_id = $1 AND lower(item) = lower($2) AND unit IS NOT DISTINCT FROM $3
                           AND checked_at IS NULL AND amount IS NOT NULL ORDER BY id LIMIT 1)
               RETURNING id""", space_id, item.strip(), unit, amount)
        if merged:
            return merged
    return await conn.fetchval("INSERT INTO shopping_items (space_id, item, amount, unit, recipe_id) VALUES ($1, $2, $3, $4, $5) RETURNING id",
                               space_id, item.strip(), amount, unit, recipe_id)


async def _own(conn: asyncpg.Connection, space_id: int, item_id: int) -> None:
    if not await conn.fetchval("SELECT 1 FROM shopping_items WHERE id = $1 AND space_id = $2", item_id, space_id):
        raise ApiError(404, "shopping.not_found")


@router.get("")
async def list_items(space=Depends(active_space), conn: asyncpg.Connection = Depends(get_conn)):
    rows = await conn.fetch(f"SELECT {COLUMNS} FROM shopping_items WHERE space_id = $1 ORDER BY checked_at IS NOT NULL, checked_at, id", space["id"])
    return [dict(r) for r in rows]


@router.post("")
async def add(body: ItemIn, space=Depends(active_space), conn: asyncpg.Connection = Depends(get_conn)):
    return {"id": await add_item(conn, space["id"], body.item, body.amount, body.unit)}


@router.post("/from-recipe")
async def from_recipe(body: FromRecipeIn, space=Depends(active_space), conn: asyncpg.Connection = Depends(get_conn)):
    recipe = await conn.fetchrow("SELECT portions FROM recipes WHERE id = $1 AND space_id = $2 AND deleted_at IS NULL", body.recipe_id, space["id"])
    if not recipe:
        raise ApiError(404, "recipe.not_found")
    rows = await conn.fetch("SELECT amount::float AS amount, unit, item FROM recipe_ingredients WHERE recipe_id = $1 ORDER BY position", body.recipe_id)
    async with conn.transaction():
        for i in scale([dict(r) for r in rows], recipe["portions"], body.portions):
            await add_item(conn, space["id"], i["item"], i["amount"], i["unit"], body.recipe_id)
    return {"ok": True}


@router.patch("/{item_id}")
async def check(item_id: int, body: CheckIn, space=Depends(active_space), conn: asyncpg.Connection = Depends(get_conn)):
    await _own(conn, space["id"], item_id)
    await conn.execute("UPDATE shopping_items SET checked_at = CASE WHEN $2 THEN now() END WHERE id = $1", item_id, body.checked)
    return {"ok": True}


@router.delete("/{item_id}")
async def remove(item_id: int, space=Depends(active_space), conn: asyncpg.Connection = Depends(get_conn)):
    await _own(conn, space["id"], item_id)
    await conn.execute("DELETE FROM shopping_items WHERE id = $1", item_id)
    return {"ok": True}


@router.post("/clear-checked")
async def clear_checked(space=Depends(active_space), conn: asyncpg.Connection = Depends(get_conn)):
    await conn.execute("DELETE FROM shopping_items WHERE space_id = $1 AND checked_at IS NOT NULL", space["id"])
    return {"ok": True}
