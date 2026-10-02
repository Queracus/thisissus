from datetime import UTC, datetime, timedelta

from tests.helpers import in_space, login, signup

SOON = datetime.now(UTC).replace(microsecond=0) + timedelta(days=7)
FRI, SAT, SUN = (SOON + timedelta(days=d) for d in range(3))
iso = lambda d: d.isoformat().replace("+00:00", "Z")  # noqa: E731


async def couple_idea(client, conn):
    """Ana + Bor share a space and an idea; client is logged in as Ana. Returns (idea_id, ana, bor, eve_space_setup)."""
    _, space_id, ana = await in_space(client, conn, "Ana")
    bor_id, bor = await signup(client, conn, "Bor")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, bor_id)
    await login(client, ana)
    idea_id = (await client.post("/api/ideas", json={"title": "Kino"})).json()["id"]
    return idea_id, ana, bor


async def act(client, idea_id, action, **body):
    return await client.post(f"/api/ideas/{idea_id}/{action}", json=body)


async def test_full_negotiation_to_scheduled_with_timeline(client, conn):
    idea_id, ana, bor = await couple_idea(client, conn)

    assert (await act(client, idea_id, "propose", slots=[iso(FRI), iso(SAT)])).status_code == 200
    await login(client, bor)
    await act(client, idea_id, "counter", slots=[iso(SUN)])
    await client.post(f"/api/ideas/{idea_id}/comments", json={"text": "Petek ne morem, mamin rojstni dan"})
    await login(client, ana)
    res = await act(client, idea_id, "accept", slot=iso(SUN))

    assert res.status_code == 200, res.text
    idea = (await client.get(f"/api/ideas/{idea_id}")).json()
    assert (idea["status"], idea["scheduled_at"]) == ("scheduled", iso(SUN))
    timeline = (await client.get(f"/api/ideas/{idea_id}/timeline")).json()
    assert [(e["actor_name"], e["kind"]) for e in timeline["events"]] == [
        ("Ana", "proposed"), ("Bor", "countered"), ("Bor", "comment"), ("Ana", "scheduled")]
    assert timeline["events"][2]["payload"]["text"] == "Petek ne morem, mamin rojstni dan"
    assert timeline["proposal"]["status"] == "accepted" and timeline["proposal"]["slots"] == [iso(SUN)]


async def test_pending_proposal_is_visible_to_the_partner(client, conn):
    idea_id, ana, bor = await couple_idea(client, conn)
    await act(client, idea_id, "propose", slots=[iso(SAT), iso(FRI)])
    await login(client, bor)

    proposal = (await client.get(f"/api/ideas/{idea_id}/timeline")).json()["proposal"]

    assert (proposal["proposed_by_name"], proposal["slots"], proposal["status"]) == ("Ana", [iso(FRI), iso(SAT)], "open")
    assert proposal["awaiting_me"] is True


async def test_refuse_returns_to_idea(client, conn):
    idea_id, ana, bor = await couple_idea(client, conn)
    await act(client, idea_id, "propose", slots=[iso(FRI)])
    await login(client, bor)

    await act(client, idea_id, "refuse")

    assert (await client.get(f"/api/ideas/{idea_id}")).json()["status"] == "idea"
    assert (await client.get(f"/api/ideas/{idea_id}/timeline")).json()["proposal"] is None


async def test_rule_violations_return_codes(client, conn):
    idea_id, ana, bor = await couple_idea(client, conn)
    await act(client, idea_id, "propose", slots=[iso(FRI)])

    own = await act(client, idea_id, "accept", slot=iso(FRI))
    past = await act(client, idea_id, "counter", slots=["2000-01-01T10:00:00Z"])
    again = await act(client, idea_id, "propose", slots=[iso(SAT)])

    assert (own.status_code, own.json()) == (409, {"code": "proposal.own_proposal"})
    assert past.json() == {"code": "proposal.slot_in_past"}
    assert again.json() == {"code": "proposal.invalid_state"}


async def test_outsiders_cannot_act_or_read(client, conn):
    idea_id, _, _ = await couple_idea(client, conn)
    await signup(client, conn, "Eve")

    assert (await act(client, idea_id, "propose", slots=[iso(FRI)])).status_code == 404
    assert (await client.get(f"/api/ideas/{idea_id}/timeline")).status_code == 404
    assert (await client.post(f"/api/ideas/{idea_id}/comments", json={"text": "hi"})).status_code == 404


async def test_reschedule_a_scheduled_date(client, conn):
    idea_id, ana, bor = await couple_idea(client, conn)
    await act(client, idea_id, "propose", slots=[iso(FRI)])
    await login(client, bor)
    await act(client, idea_id, "accept", slot=iso(FRI))

    await act(client, idea_id, "counter", slots=[iso(SAT)])

    idea = (await client.get(f"/api/ideas/{idea_id}")).json()
    assert (idea["status"], idea["scheduled_at"]) == ("pending", None)
