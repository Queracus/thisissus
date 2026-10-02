from datetime import datetime

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import AwareDatetime, BaseModel, Field, ValidationInfo, field_validator

from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError
from app.policy import active_space, scope_sql

router = APIRouter(prefix="/dates")
COLUMNS = "id, space_id, title, starts_at, ends_at, place_name, lat, lon, cost::float AS cost, created_by, created_at"


class DateIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None = None
    place_name: str | None = Field(default=None, max_length=200)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    cost: float | None = Field(default=None, ge=0)

    @field_validator("ends_at")
    @classmethod
    def ends_after_start(cls, v, info: ValidationInfo):
        if v and info.data.get("starts_at") and v < info.data["starts_at"]:
            raise ValueError("ends before it starts")
        return v


class DateOut(BaseModel):
    id: int
    space_id: int
    title: str
    starts_at: datetime
    ends_at: datetime | None
    place_name: str | None
    lat: float | None
    lon: float | None
    cost: float | None
    created_by: int | None
    created_at: datetime


async def visible_date(conn: asyncpg.Connection, user_id: int, date_id: int) -> asyncpg.Record:
    """A live date in any space the user belongs to, else 404."""
    scope, params = scope_sql(user_id, "space_id", 2)
    row = await conn.fetchrow(f"SELECT {COLUMNS} FROM dates WHERE id = $1 AND deleted_at IS NULL AND {scope}", date_id, *params)
    if not row:
        raise ApiError(404, "date.not_found")
    return row


@router.get("", response_model=list[DateOut])
async def list_dates(space: asyncpg.Record = Depends(active_space), conn: asyncpg.Connection = Depends(get_conn)):
    rows = await conn.fetch(f"SELECT {COLUMNS} FROM dates WHERE space_id = $1 AND deleted_at IS NULL ORDER BY starts_at DESC, id DESC", space["id"])
    return [dict(r) for r in rows]


@router.post("", response_model=DateOut)
async def create_date(body: DateIn, space: asyncpg.Record = Depends(active_space), user: asyncpg.Record = Depends(current_user),
                      conn: asyncpg.Connection = Depends(get_conn)):
    return dict(await conn.fetchrow(
        f"""INSERT INTO dates (space_id, title, starts_at, ends_at, place_name, lat, lon, cost, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING {COLUMNS}""",
        space["id"], body.title, body.starts_at, body.ends_at, body.place_name, body.lat, body.lon, body.cost, user["id"]))


@router.get("/{date_id}", response_model=DateOut)
async def get_date(date_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return dict(await visible_date(conn, user["id"], date_id))


@router.put("/{date_id}", response_model=DateOut)
async def update_date(date_id: int, body: DateIn, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await visible_date(conn, user["id"], date_id)
    return dict(await conn.fetchrow(
        f"""UPDATE dates SET title = $2, starts_at = $3, ends_at = $4, place_name = $5, lat = $6, lon = $7, cost = $8, updated_at = now()
            WHERE id = $1 RETURNING {COLUMNS}""",
        date_id, body.title, body.starts_at, body.ends_at, body.place_name, body.lat, body.lon, body.cost))


@router.delete("/{date_id}")
async def delete_date(date_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await visible_date(conn, user["id"], date_id)
    await conn.execute("UPDATE dates SET deleted_at = now() WHERE id = $1", date_id)
    return {"ok": True}
