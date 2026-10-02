"""Home screen: what needs me now, what's coming, and memories."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import asyncpg
from fastapi import APIRouter, Depends

from app import config
from app.auth.deps import current_user
from app.db import get_conn
from app.policy import active_space
from app.routers.ideas import INVITEE_IDS

router = APIRouter()
LOCAL_DAY = f"(d.starts_at AT TIME ZONE '{config.TIMEZONE}')::date"
FIRST_PHOTO = """(SELECT m.id FROM date_media dm JOIN media m ON m.id = dm.media_id
                  WHERE dm.date_id = d.id AND m.status = 'ready' AND m.deleted_at IS NULL ORDER BY dm.position LIMIT 1)"""


async def upcoming(conn: asyncpg.Connection, space_id: int) -> list[dict]:
    rows = await conn.fetch("""SELECT id, title, scheduled_at FROM ideas WHERE space_id = $1 AND deleted_at IS NULL AND status = 'scheduled'
                               AND scheduled_at BETWEEN now() AND now() + interval '30 days' ORDER BY scheduled_at""", space_id)
    return [dict(r) for r in rows]


async def awaiting_me(conn: asyncpg.Connection, space_id: int, user_id: int) -> list[dict]:
    rows = await conn.fetch(
        f"""SELECT i.id, i.title, u.display_name AS proposed_by_name,
                   (SELECT array_agg(starts_at ORDER BY starts_at) FROM proposal_slots WHERE proposal_id = p.id) AS slots
            FROM ideas i JOIN proposals p ON p.idea_id = i.id AND p.status = 'open' LEFT JOIN users u ON u.id = p.proposed_by
            WHERE i.space_id = $1 AND i.deleted_at IS NULL AND i.status = 'pending' AND p.proposed_by IS DISTINCT FROM $2
              AND NOT EXISTS (SELECT 1 FROM proposal_responses r WHERE r.proposal_id = p.id AND r.user_id = $2)
              AND (i.suggested_by = $2 OR $2 IN ({INVITEE_IDS.format(i='i')}))
            ORDER BY p.created_at""", space_id, user_id)
    return [dict(r) for r in rows]


async def on_this_day(conn: asyncpg.Connection, space_id: int, today: date) -> list[dict]:
    """Same calendar day in earlier years. In a non-leap year, 29 February memories show on 28 February."""
    rows = await conn.fetch(
        f"""SELECT d.id, d.title, d.starts_at, $2::int - extract(year FROM {LOCAL_DAY})::int AS years_ago, {FIRST_PHOTO} AS thumb_id
            FROM dates d
            WHERE d.space_id = $1 AND d.deleted_at IS NULL AND extract(year FROM {LOCAL_DAY}) < $2
              AND ((extract(month FROM {LOCAL_DAY}) = $3 AND extract(day FROM {LOCAL_DAY}) = $4)
                   OR ($5 AND extract(month FROM {LOCAL_DAY}) = 2 AND extract(day FROM {LOCAL_DAY}) = 29))
            ORDER BY d.starts_at DESC""",
        space_id, today.year, today.month, today.day, (today.month, today.day) == (2, 28) and not _leap(today.year))
    return [dict(r) for r in rows]


def _leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


async def stats(conn: asyncpg.Connection, space_id: int, today: date) -> dict:
    base = "FROM dates d WHERE d.space_id = $1 AND d.deleted_at IS NULL"
    totals = await conn.fetchrow(
        f"""SELECT count(*) AS total, count(*) FILTER (WHERE extract(year FROM {LOCAL_DAY}) = $2) AS this_year,
                   coalesce(sum(d.cost) FILTER (WHERE extract(year FROM {LOCAL_DAY}) = $2), 0)::float AS spent_this_year {base}""",
        space_id, today.year)
    per_month = await conn.fetch(
        f"""SELECT to_char({LOCAL_DAY}, 'YYYY-MM') AS month, count(*) AS count {base}
              AND {LOCAL_DAY} >= (date_trunc('month', $2::date) - interval '11 months')::date AND {LOCAL_DAY} <= $2
            GROUP BY 1 ORDER BY 1""", space_id, today)
    top_tags = await conn.fetch(
        """SELECT t.id, t.name, t.starter_key, count(*) AS count FROM date_tags dt JOIN tags t ON t.id = dt.tag_id
           JOIN dates d ON d.id = dt.date_id WHERE d.space_id = $1 AND d.deleted_at IS NULL
           GROUP BY t.id ORDER BY count(*) DESC, t.id LIMIT 5""", space_id)
    return {**dict(totals), "per_month": [dict(r) for r in per_month], "top_tags": [dict(r) for r in top_tags]}


@router.get("/dashboard")
async def dashboard(today: date | None = None, space=Depends(active_space), user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    """`today` (YYYY-MM-DD) defaults to the current day in the app's timezone."""
    today = today or datetime.now(ZoneInfo(config.TIMEZONE)).date()
    return {"upcoming": await upcoming(conn, space["id"]), "awaiting_me": await awaiting_me(conn, space["id"], user["id"]),
            "on_this_day": await on_this_day(conn, space["id"], today), "stats": await stats(conn, space["id"], today)}
