from app.reminders import tick
from tests.helpers import in_space, login, signup


async def couple(client, conn):
    ana_id, space_id, ana = await in_space(client, conn, "Ana")
    bor_id, bor = await signup(client, conn, "Bor")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, bor_id)
    await login(client, ana)
    return space_id, ana_id, bor_id


async def notes(conn, kind):
    return sorted((r["user_id"], r["payload"]["title"]) for r in await conn.fetch("SELECT user_id, payload FROM notifications WHERE kind = $1", kind))


async def scheduled_idea(conn, space_id, ana_id, title, offset):
    return await conn.fetchval(
        f"INSERT INTO ideas (space_id, title, status, scheduled_at, suggested_by) VALUES ($1, $2, 'scheduled', now() + interval '{offset}', $3) RETURNING id",
        space_id, title, ana_id)


async def test_reminds_everyone_the_day_before_once(client, conn):
    space_id, ana_id, bor_id = await couple(client, conn)
    await scheduled_idea(conn, space_id, ana_id, "Kino", "20 hours")
    await scheduled_idea(conn, space_id, ana_id, "Later", "3 days")
    await scheduled_idea(conn, space_id, ana_id, "Past", "-2 hours")

    await tick(conn, {})
    await tick(conn, {})

    assert await notes(conn, "date.tomorrow") == [(ana_id, "Kino"), (bor_id, "Kino")]


async def test_rescheduled_date_gets_a_new_reminder(client, conn):
    space_id, ana_id, bor_id = await couple(client, conn)
    idea_id = await scheduled_idea(conn, space_id, ana_id, "Kino", "20 hours")
    await tick(conn, {})

    await conn.execute("UPDATE ideas SET scheduled_at = now() + interval '22 hours' WHERE id = $1", idea_id)
    await tick(conn, {})

    assert len(await notes(conn, "date.tomorrow")) == 4


async def test_unrated_dates_remind_only_those_who_did_not_rate(client, conn):
    space_id, ana_id, bor_id = await couple(client, conn)
    date_id = await conn.fetchval(
        "INSERT INTO dates (space_id, title, starts_at) VALUES ($1, 'Picnic', now() - interval '4 days') RETURNING id", space_id)
    await conn.execute("INSERT INTO date_reviews (date_id, user_id, rating, again) VALUES ($1, $2, 5, 'yes')", date_id, ana_id)

    await tick(conn, {})
    await tick(conn, {})

    assert await notes(conn, "rating.missing") == [(bor_id, "Picnic")]


async def test_no_rating_nag_too_early_or_for_old_history(client, conn):
    space_id, _, _ = await couple(client, conn)
    for title, ago in (("Yesterday", "1 day"), ("Last year", "365 days")):
        await conn.execute(f"INSERT INTO dates (space_id, title, starts_at) VALUES ($1, $2, now() - interval '{ago}')", space_id, title)

    await tick(conn, {})

    assert await notes(conn, "rating.missing") == []


async def test_multi_day_trip_counts_from_its_end(client, conn):
    space_id, ana_id, bor_id = await couple(client, conn)
    await conn.execute("""INSERT INTO dates (space_id, title, starts_at, ends_at)
                          VALUES ($1, 'Trip', now() - interval '6 days', now() - interval '1 day')""", space_id)

    await tick(conn, {})

    assert await notes(conn, "rating.missing") == []
