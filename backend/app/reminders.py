"""Worker job reminders.tick (hourly): nudges that nobody has to remember to send."""
import asyncpg

from app.notify import notify
from app.routers.ideas import participants

RATE_AFTER_DAYS, RATE_UNTIL_DAYS = 3, 10  # ask for ratings 3–10 days after a date ended (not for old history)


async def _once(conn: asyncpg.Connection, key: str, user_ids) -> list[int]:
    """Users who haven't received reminder `key` yet; marks them as sent."""
    rows = await conn.fetch(
        """INSERT INTO reminders_sent (key, user_id) SELECT $1, u FROM unnest($2::bigint[]) AS u
           ON CONFLICT DO NOTHING RETURNING user_id""", key, sorted(user_ids))
    return [r["user_id"] for r in rows]


async def tick(conn: asyncpg.Connection, payload: dict) -> None:
    # A scheduled date in the next 25 hours (an hour of slack so a late tick doesn't miss it).
    for idea in await conn.fetch(
            """SELECT id, title, scheduled_at FROM ideas
               WHERE status = 'scheduled' AND deleted_at IS NULL AND scheduled_at > now() AND scheduled_at <= now() + interval '25 hours'"""):
        key = f"date.tomorrow:{idea['id']}:{idea['scheduled_at'].isoformat()}"  # rescheduling = a new reminder
        targets = await _once(conn, key, await participants(conn, idea["id"]))
        await notify(conn, None, "date.tomorrow",
                     {"idea_id": idea["id"], "title": idea["title"], "slot": idea["scheduled_at"].isoformat()}, targets)

    # Dates that ended a few days ago and still miss someone's rating.
    for row in await conn.fetch(
            """SELECT d.id, d.title, array_agg(m.user_id) AS missing FROM dates d
               JOIN space_members m ON m.space_id = d.space_id
               WHERE d.deleted_at IS NULL
                 AND coalesce(d.ends_at, d.starts_at) BETWEEN now() - make_interval(days => $2) AND now() - make_interval(days => $1)
                 AND NOT EXISTS (SELECT 1 FROM date_reviews r WHERE r.date_id = d.id AND r.user_id = m.user_id)
               GROUP BY d.id""", RATE_AFTER_DAYS, RATE_UNTIL_DAYS):
        targets = await _once(conn, f"rating.missing:{row['id']}", row["missing"])
        await notify(conn, None, "rating.missing", {"date_id": row["id"], "title": row["title"]}, targets)

    # Recipes cooked a few days ago that someone in the space hasn't rated.
    for row in await conn.fetch(
            """SELECT r.id, r.title, array_agg(DISTINCT m.user_id) AS missing FROM recipes r
               JOIN recipe_cooks c ON c.recipe_id = r.id JOIN space_members m ON m.space_id = r.space_id
               WHERE r.deleted_at IS NULL AND c.created_at BETWEEN now() - make_interval(days => $2) AND now() - make_interval(days => $1)
                 AND NOT EXISTS (SELECT 1 FROM recipe_reviews x WHERE x.recipe_id = r.id AND x.user_id = m.user_id)
               GROUP BY r.id""", RATE_AFTER_DAYS, RATE_UNTIL_DAYS):
        targets = await _once(conn, f"recipe.rating_missing:{row['id']}", row["missing"])
        await notify(conn, None, "recipe.rating_missing", {"recipe_id": row["id"], "title": row["title"]}, targets)
