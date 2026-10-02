from datetime import UTC, datetime, timedelta

from tests.helpers import in_space, login, signup

iso = lambda d: d.isoformat().replace("+00:00", "Z")  # noqa: E731


async def couple(client, conn):
    ana_id, space_id, ana = await in_space(client, conn, "Ana")
    bor_id, bor = await signup(client, conn, "Bor")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, bor_id)
    await login(client, ana)
    return space_id, ana, bor


async def dash(client, today=None):
    res = await client.get("/api/dashboard" + (f"?today={today}" if today else ""))
    assert res.status_code == 200, res.text
    return res.json()


async def test_upcoming_scheduled_dates(client, conn):
    space_id, ana, bor = await couple(client, conn)
    soon = (datetime.now(UTC) + timedelta(days=5)).replace(microsecond=0)
    later = (datetime.now(UTC) + timedelta(days=60)).replace(microsecond=0)
    for title, when in (("Kino", soon), ("Morje", later)):
        idea_id = (await client.post("/api/ideas", json={"title": title})).json()["id"]
        await client.post(f"/api/ideas/{idea_id}/propose", json={"slots": [iso(when)]})
        await login(client, bor)
        await client.post(f"/api/ideas/{idea_id}/accept", json={"slot": iso(when)})
        await login(client, ana)

    assert [u["title"] for u in (await dash(client))["upcoming"]] == ["Kino"]


async def test_proposals_awaiting_my_answer(client, conn):
    space_id, ana, bor = await couple(client, conn)
    idea_id = (await client.post("/api/ideas", json={"title": "Piknik"})).json()["id"]
    await client.post(f"/api/ideas/{idea_id}/propose", json={"slots": [iso(datetime.now(UTC) + timedelta(days=3))]})

    assert (await dash(client))["awaiting_me"] == []  # my own proposal
    await login(client, bor)
    assert [(a["title"], a["proposed_by_name"]) for a in (await dash(client))["awaiting_me"]] == [("Piknik", "Ana")]


async def test_on_this_day_shows_earlier_years(client, conn):
    await couple(client, conn)
    for title, when in (("Prvi zmenek", "2024-06-14T19:00:00Z"), ("Lani", "2025-06-14T12:00:00Z"),
                        ("Ta teden", "2025-06-16T12:00:00Z"), ("Letos", "2026-06-14T09:00:00Z")):
        await client.post("/api/dates", json={"title": title, "starts_at": when})

    memories = (await dash(client, "2026-06-14"))["on_this_day"]

    assert [(m["title"], m["years_ago"]) for m in memories] == [("Lani", 1), ("Prvi zmenek", 2)]


async def test_leap_day_memories_show_on_feb_28(client, conn):
    await couple(client, conn)
    await client.post("/api/dates", json={"title": "Prestopni", "starts_at": "2024-02-29T18:00:00Z"})

    assert [m["title"] for m in (await dash(client, "2025-02-28"))["on_this_day"]] == ["Prestopni"]
    assert (await dash(client, "2028-02-28"))["on_this_day"] == []  # 2028 has its own Feb 29


async def test_stats(client, conn):
    await couple(client, conn)
    food = next(t["id"] for t in (await client.get("/api/tags")).json() if t["starter_key"] == "food")
    for when, cost, tags in (("2026-01-10T12:00:00Z", 20, [food]), ("2026-01-20T12:00:00Z", 30, [food]),
                             ("2026-03-05T12:00:00Z", None, []), ("2025-12-31T12:00:00Z", 100, [food])):
        await client.post("/api/dates", json={"title": "x", "starts_at": when, "cost": cost, "tag_ids": tags})

    stats = (await dash(client, "2026-03-10"))["stats"]

    assert (stats["total"], stats["this_year"], stats["spent_this_year"]) == (4, 3, 50.0)
    assert {m["month"]: m["count"] for m in stats["per_month"]} == {"2025-12": 1, "2026-01": 2, "2026-03": 1}
    assert [(t["starter_key"], t["count"]) for t in stats["top_tags"]] == [("food", 3)]


async def test_other_spaces_stay_out(client, conn):
    await couple(client, conn)
    await client.post("/api/dates", json={"title": "Ours", "starts_at": "2025-06-14T12:00:00Z"})
    await in_space(client, conn, "Eve")

    d = await dash(client, "2026-06-14")

    assert (d["on_this_day"], d["stats"]["total"], d["upcoming"], d["awaiting_me"]) == ([], 0, [], [])
