from datetime import UTC, datetime, timedelta

from tests.helpers import in_space, login, signup

SAT = (datetime.now(UTC) + timedelta(days=10)).replace(microsecond=0)
iso = lambda d: d.isoformat().replace("+00:00", "Z")  # noqa: E731


async def setup(client, conn):
    _, space_id, ana = await in_space(client, conn, "Ana")
    bor_id, bor = await signup(client, conn, "Bor")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, bor_id)
    await login(client, ana)
    tags = {t["starter_key"]: t["id"] for t in (await client.get("/api/tags")).json()}

    async def idea(title, **kw):
        return (await client.post("/api/ideas", json={"title": title, **kw})).json()["id"]

    ids = {
        "hike": await idea("Hike", est_cost=0, season="summer", tag_ids=[tags["outdoors"], tags["cheap"]]),
        "opera": await idea("Opera", est_cost=120, season="winter", tag_ids=[tags["culture"]]),
        "kino": await idea("Kino", est_cost=20),
        "gone": await idea("Archived"),
        "planned": await idea("Planned"),
    }
    await client.post(f"/api/ideas/{ids['gone']}/not-for-me")
    await client.post(f"/api/ideas/{ids['planned']}/propose", json={"slots": [iso(SAT)]})
    await login(client, bor)
    await client.post(f"/api/ideas/{ids['planned']}/accept", json={"slot": iso(SAT)})
    return ids, tags


async def picks(client, query="", n=40):
    return {(await client.get(f"/api/ideas/random?{query}")).json()["title"] for _ in range(n)}


async def test_random_only_picks_open_ideas(client, conn):
    await setup(client, conn)

    assert await picks(client) == {"Hike", "Opera", "Kino"}


async def test_random_respects_filters(client, conn):
    _, tags = await setup(client, conn)

    assert await picks(client, f"tag={tags['cheap']}", 5) == {"Hike"}
    assert await picks(client, "max_cost=50") == {"Hike", "Kino"}
    assert await picks(client, "season=winter", 5) == {"Opera"}


async def test_random_with_no_match_returns_null(client, conn):
    await setup(client, conn)

    res = await client.get("/api/ideas/random?max_cost=0&season=winter")

    assert (res.status_code, res.json()) == (200, None)


async def test_calendar_lists_scheduled_ideas_in_range(client, conn):
    await setup(client, conn)

    inside = (await client.get(f"/api/ideas/calendar?from={iso(SAT - timedelta(days=1))}&to={iso(SAT + timedelta(days=1))}")).json()
    outside = (await client.get(f"/api/ideas/calendar?from={iso(SAT + timedelta(days=2))}&to={iso(SAT + timedelta(days=9))}")).json()

    assert [(e["title"], e["scheduled_at"]) for e in inside] == [("Planned", iso(SAT))]
    assert outside == []
