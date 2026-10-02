from datetime import UTC, datetime, timedelta

from tests.helpers import in_space, login, signup

SAT = (datetime.now(UTC) + timedelta(days=10)).replace(microsecond=0)
iso = lambda d: d.isoformat().replace("+00:00", "Z")  # noqa: E731


async def trio(client, conn):
    """Ana (logged in), Bor, Eve share a space."""
    ana_id, space_id, ana = await in_space(client, conn, "Ana")
    people = {"ana": ana}
    for name in ("Bor", "Eve"):
        uid, dev = await signup(client, conn, name)
        await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, uid)
        people[name.lower()] = dev
    await login(client, ana)
    return people


async def kinds(client):
    return [(n["kind"], n["payload"]["actor_name"]) for n in (await client.get("/api/notifications")).json()["items"]]


async def test_new_idea_notifies_invitees_but_not_the_author(client, conn):
    p = await trio(client, conn)

    await client.post("/api/ideas", json={"title": "Kino"})

    assert await kinds(client) == []
    for who in ("bor", "eve"):
        await login(client, p[who])
        assert await kinds(client) == [("idea.created", "Ana")]


async def test_negotiation_steps_notify_the_other_participants(client, conn):
    p = await trio(client, conn)
    idea_id = (await client.post("/api/ideas", json={"title": "Kino"})).json()["id"]
    await client.post(f"/api/ideas/{idea_id}/propose", json={"slots": [iso(SAT)]})
    await login(client, p["bor"])
    await client.post(f"/api/ideas/{idea_id}/accept", json={"slot": iso(SAT)})
    await client.post(f"/api/ideas/{idea_id}/comments", json={"text": "Juhu"})

    await login(client, p["ana"])
    assert await kinds(client) == [("idea.comment", "Bor"), ("proposal.accepted", "Bor")]
    await login(client, p["eve"])
    assert await kinds(client) == [("idea.comment", "Bor"), ("proposal.accepted", "Bor"), ("proposal.created", "Ana"), ("idea.created", "Ana")]


async def test_payload_links_to_the_idea(client, conn):
    p = await trio(client, conn)
    idea_id = (await client.post("/api/ideas", json={"title": "Kino"})).json()["id"]
    await login(client, p["bor"])

    note = (await client.get("/api/notifications")).json()["items"][0]

    assert (note["payload"]["idea_id"], note["payload"]["title"], note["read_at"]) == (idea_id, "Kino", None)


async def test_unread_count_and_mark_read(client, conn):
    p = await trio(client, conn)
    await client.post("/api/ideas", json={"title": "Kino"})
    await client.post("/api/ideas", json={"title": "Opera"})
    await login(client, p["bor"])
    first = (await client.get("/api/notifications")).json()
    assert first["unread"] == 2

    await client.post("/api/notifications/read", json={"ids": [first["items"][0]["id"]]})
    assert (await client.get("/api/notifications")).json()["unread"] == 1
    await client.post("/api/notifications/read", json={})
    assert (await client.get("/api/notifications")).json()["unread"] == 0


async def test_cannot_mark_someone_elses_notification(client, conn):
    p = await trio(client, conn)
    await client.post("/api/ideas", json={"title": "Kino"})
    await login(client, p["bor"])
    bor_note = (await client.get("/api/notifications")).json()["items"][0]["id"]
    await login(client, p["eve"])

    await client.post("/api/notifications/read", json={"ids": [bor_note]})

    await login(client, p["bor"])
    assert (await client.get("/api/notifications")).json()["unread"] == 1


async def test_push_job_is_queued_per_notification_batch(client, conn):
    await trio(client, conn)

    await client.post("/api/ideas", json={"title": "Kino"})

    payload = await conn.fetchval("SELECT payload FROM jobs WHERE kind = 'push.send' ORDER BY id DESC LIMIT 1")
    assert len(payload["notification_ids"]) == 2
