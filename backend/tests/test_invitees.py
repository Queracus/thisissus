from datetime import UTC, datetime, timedelta

from tests.helpers import in_space, login, signup

SAT = (datetime.now(UTC) + timedelta(days=10)).replace(microsecond=0)
iso = lambda d: d.isoformat().replace("+00:00", "Z")  # noqa: E731


async def family(client, conn):
    """Ana (logged in) + Bor + Eve in one space. Returns ids and devices."""
    ana_id, space_id, ana = await in_space(client, conn, "Ana")
    people = {"ana": (ana_id, ana)}
    for name in ("Bor", "Eve"):
        uid, dev = await signup(client, conn, name)
        await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, uid)
        people[name.lower()] = (uid, dev)
    await login(client, ana)
    return people


async def test_only_invited_people_take_part(client, conn):
    p = await family(client, conn)
    idea_id = (await client.post("/api/ideas", json={"title": "Kino", "invitee_ids": [p["bor"][0]]})).json()["id"]
    await client.post(f"/api/ideas/{idea_id}/propose", json={"slots": [iso(SAT)]})

    await login(client, p["eve"][1])
    eve = await client.post(f"/api/ideas/{idea_id}/accept", json={"slot": iso(SAT)})
    await login(client, p["bor"][1])
    bor = await client.post(f"/api/ideas/{idea_id}/accept", json={"slot": iso(SAT)})

    assert eve.json() == {"code": "proposal.not_participant"}
    assert bor.json()["status"] == "scheduled"


async def test_everyone_invited_by_default_and_pending_names_shown(client, conn):
    p = await family(client, conn)
    idea_id = (await client.post("/api/ideas", json={"title": "Piknik"})).json()["id"]
    assert sorted(i["display_name"] for i in (await client.get(f"/api/ideas/{idea_id}")).json()["invitees"]) == ["Bor", "Eve"]
    await client.post(f"/api/ideas/{idea_id}/propose", json={"slots": [iso(SAT)]})
    await login(client, p["bor"][1])
    await client.post(f"/api/ideas/{idea_id}/accept", json={"slot": iso(SAT)})

    proposal = (await client.get(f"/api/ideas/{idea_id}/timeline")).json()["proposal"]

    assert proposal["pending_names"] == ["Eve"]
    assert (await client.get(f"/api/ideas/{idea_id}")).json()["status"] == "pending"


async def test_invitees_must_be_space_members(client, conn):
    await family(client, conn)
    outsider = await conn.fetchval("INSERT INTO users (display_name) VALUES ('Mallory') RETURNING id")

    res = await client.post("/api/ideas", json={"title": "Kino", "invitee_ids": [outsider]})

    assert res.json() == {"code": "idea.invalid_invitee"}


async def test_not_for_me_archives_and_reopen_restores(client, conn):
    p = await family(client, conn)
    idea_id = (await client.post("/api/ideas", json={"title": "Opera"})).json()["id"]
    await login(client, p["bor"][1])

    await client.post(f"/api/ideas/{idea_id}/not-for-me")

    assert (await client.get("/api/ideas")).json() == []
    assert [i["title"] for i in (await client.get("/api/ideas?archived=true")).json()] == ["Opera"]
    await client.post(f"/api/ideas/{idea_id}/reopen")
    assert [i["status"] for i in (await client.get("/api/ideas")).json()] == ["idea"]


async def test_explicit_invitees_are_returned_and_kept(client, conn):
    p = await family(client, conn)
    idea_id = (await client.post("/api/ideas", json={"title": "Kino", "invitee_ids": [p["eve"][0]]})).json()["id"]

    idea = (await client.get(f"/api/ideas/{idea_id}")).json()

    assert idea["invitee_ids"] == [p["eve"][0]]
    assert [i["display_name"] for i in idea["invitees"]] == ["Eve"]
    default = (await client.post("/api/ideas", json={"title": "Vsi"})).json()
    assert default["invitee_ids"] is None
