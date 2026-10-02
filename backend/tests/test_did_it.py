from datetime import UTC, datetime, timedelta

from tests.helpers import in_space, login, signup

SAT = (datetime.now(UTC) + timedelta(days=10)).replace(microsecond=0)
iso = lambda d: d.isoformat().replace("+00:00", "Z")  # noqa: E731


async def scheduled_idea(client, conn):
    _, space_id, ana = await in_space(client, conn, "Ana")
    bor_id, bor = await signup(client, conn, "Bor")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, bor_id)
    await login(client, ana)
    food = next(t["id"] for t in (await client.get("/api/tags")).json() if t["starter_key"] == "food")
    idea_id = (await client.post("/api/ideas", json={"title": "Ramen", "est_cost": 30, "tag_ids": [food]})).json()["id"]
    await client.post(f"/api/ideas/{idea_id}/propose", json={"slots": [iso(SAT)]})
    await login(client, bor)
    await client.post(f"/api/ideas/{idea_id}/accept", json={"slot": iso(SAT)})
    return idea_id, food


async def test_we_did_it_creates_a_prefilled_date(client, conn):
    idea_id, food = await scheduled_idea(client, conn)

    res = await client.post(f"/api/ideas/{idea_id}/did-it", json={"archive": False})

    assert res.status_code == 200, res.text
    date = (await client.get(f"/api/dates/{res.json()['date_id']}")).json()
    assert (date["title"], date["starts_at"], date["cost"], date["idea_id"]) == ("Ramen", iso(SAT), 30.0, idea_id)
    assert [t["id"] for t in date["tags"]] == [food]
    idea = (await client.get(f"/api/ideas/{idea_id}")).json()
    assert (idea["status"], idea["times_done"], idea["scheduled_at"]) == ("idea", 1, None)
    kinds = [e["kind"] for e in (await client.get(f"/api/ideas/{idea_id}/timeline")).json()["events"]]
    assert kinds[-1] == "done"


async def test_idea_can_be_repeated_or_archived(client, conn):
    idea_id, _ = await scheduled_idea(client, conn)
    await client.post(f"/api/ideas/{idea_id}/did-it", json={"archive": False})

    second = await client.post(f"/api/ideas/{idea_id}/did-it", json={"archive": True})

    idea = (await client.get(f"/api/ideas/{idea_id}")).json()
    assert (idea["status"], idea["times_done"]) == ("archived", 2)
    assert second.json()["date_id"] != idea_id
    assert len((await client.get("/api/dates")).json()) == 2


async def test_did_it_without_a_time_uses_now(client, conn):
    await in_space(client, conn)
    idea_id = (await client.post("/api/ideas", json={"title": "Sprehod"})).json()["id"]

    date_id = (await client.post(f"/api/ideas/{idea_id}/did-it", json={"archive": False})).json()["date_id"]

    starts = datetime.fromisoformat((await client.get(f"/api/dates/{date_id}")).json()["starts_at"].replace("Z", "+00:00"))
    assert abs(starts - datetime.now(UTC)) < timedelta(minutes=1)
