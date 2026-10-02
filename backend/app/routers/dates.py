from datetime import datetime
from typing import Literal

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import AwareDatetime, BaseModel, Field, ValidationInfo, field_validator

from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError
from app.policy import active_space, scope_sql
from app.routers.tags import set_tags, tags_json

router = APIRouter(prefix="/dates")
COLUMNS = """id, space_id, title, starts_at, ends_at, place_name, lat, lon, cost::float AS cost, created_by, created_at,
             (SELECT avg(r.rating)::float FROM date_reviews r WHERE r.date_id = dates.id) AS avg_rating,
             """ + tags_json("date_tags", "date_id", "dates.id") + " AS tags"


class DateIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None = None
    place_name: str | None = Field(default=None, max_length=200)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    cost: float | None = Field(default=None, ge=0)
    tag_ids: list[int] = []

    @field_validator("ends_at")
    @classmethod
    def ends_after_start(cls, v, info: ValidationInfo):
        if v and info.data.get("starts_at") and v < info.data["starts_at"]:
            raise ValueError("ends before it starts")
        return v


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    again: Literal["yes", "maybe", "no"]
    notes: str | None = Field(default=None, max_length=2000)


class ReviewOut(BaseModel):
    user_id: int
    display_name: str
    rating: int
    again: str
    notes: str | None


class PhotoOut(BaseModel):
    id: int
    kind: str
    status: str
    width: int | None
    height: int | None
    duration_s: float | None
    caption: str | None
    position: int


class TagOut(BaseModel):
    id: int
    name: str
    starter_key: str | None


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
    avg_rating: float | None
    tags: list[TagOut]
    reviews: list[ReviewOut] = []
    photos: list[PhotoOut] = []


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


@router.get("/map")  # before /{date_id} so "map" isn't parsed as an id
async def map_points(space: asyncpg.Record = Depends(active_space), conn: asyncpg.Connection = Depends(get_conn)):
    rows = await conn.fetch(
        """SELECT d.id, d.title, d.starts_at, d.lat, d.lon,
                  (SELECT m.id FROM date_media dm JOIN media m ON m.id = dm.media_id
                   WHERE dm.date_id = d.id AND m.status = 'ready' AND m.deleted_at IS NULL ORDER BY dm.position LIMIT 1) AS thumb_id
           FROM dates d WHERE d.space_id = $1 AND d.deleted_at IS NULL AND d.lat IS NOT NULL AND d.lon IS NOT NULL
           ORDER BY d.starts_at DESC""", space["id"])
    return [dict(r) for r in rows]


@router.get("/{date_id}/suggested-location")
async def suggested_location(date_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    """GPS from the first photo that has it (members only; derivatives and shares never expose this)."""
    await visible_date(conn, user["id"], date_id)
    row = await conn.fetchrow(
        """SELECT (m.exif->>'lat')::float AS lat, (m.exif->>'lon')::float AS lon FROM date_media dm JOIN media m ON m.id = dm.media_id
           WHERE dm.date_id = $1 AND m.deleted_at IS NULL AND m.exif ? 'lat' ORDER BY dm.position LIMIT 1""", date_id)
    return dict(row) if row else None


@router.post("", response_model=DateOut)
async def create_date(body: DateIn, space: asyncpg.Record = Depends(active_space), user: asyncpg.Record = Depends(current_user),
                      conn: asyncpg.Connection = Depends(get_conn)):
    async with conn.transaction():
        date_id = await conn.fetchval(
            """INSERT INTO dates (space_id, title, starts_at, ends_at, place_name, lat, lon, cost, created_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING id""",
            space["id"], body.title, body.starts_at, body.ends_at, body.place_name, body.lat, body.lon, body.cost, user["id"])
        await set_tags(conn, "date_tags", "date_id", date_id, space["id"], body.tag_ids)
    return dict(await visible_date(conn, user["id"], date_id))


@router.get("/{date_id}", response_model=DateOut)
async def get_date(date_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    date = dict(await visible_date(conn, user["id"], date_id))
    from app.routers.photos import date_photos
    date["photos"] = await date_photos(conn, date_id)
    date["reviews"] = [dict(r) for r in await conn.fetch(
        """SELECT r.user_id, u.display_name, r.rating, r.again, r.notes FROM date_reviews r JOIN users u ON u.id = r.user_id
           WHERE r.date_id = $1 ORDER BY r.updated_at""", date_id)]
    return date


@router.put("/{date_id}", response_model=DateOut)
async def update_date(date_id: int, body: DateIn, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    date = await visible_date(conn, user["id"], date_id)
    async with conn.transaction():
        await conn.execute(
            """UPDATE dates SET title = $2, starts_at = $3, ends_at = $4, place_name = $5, lat = $6, lon = $7, cost = $8, updated_at = now()
               WHERE id = $1""",
            date_id, body.title, body.starts_at, body.ends_at, body.place_name, body.lat, body.lon, body.cost)
        await set_tags(conn, "date_tags", "date_id", date_id, date["space_id"], body.tag_ids)
    return dict(await visible_date(conn, user["id"], date_id))


@router.delete("/{date_id}")
async def delete_date(date_id: int, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await visible_date(conn, user["id"], date_id)
    await conn.execute("UPDATE dates SET deleted_at = now() WHERE id = $1", date_id)
    return {"ok": True}


@router.put("/{date_id}/review")
async def put_review(date_id: int, body: ReviewIn, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    """Create or replace the caller's own review."""
    await visible_date(conn, user["id"], date_id)
    await conn.execute(
        """INSERT INTO date_reviews (date_id, user_id, rating, again, notes) VALUES ($1, $2, $3, $4, $5)
           ON CONFLICT (date_id, user_id) DO UPDATE SET rating = $3, again = $4, notes = $5, updated_at = now()""",
        date_id, user["id"], body.rating, body.again, body.notes)
    return {"ok": True}
