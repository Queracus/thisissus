from tests.helpers import in_space, login, signup

PICNIC = {"title": "Picnic at Bled", "starts_at": "2026-06-14T12:00:00+02:00", "place_name": "Bled", "cost": 12.5}


async def test_logged_date_appears_in_the_spaces_list(client, conn):
    await in_space(client, conn)

    res = await client.post("/api/dates", json=PICNIC)

    assert res.status_code == 200, res.text
    dates = (await client.get("/api/dates")).json()
    assert [(d["title"], d["place_name"], d["cost"]) for d in dates] == [("Picnic at Bled", "Bled", 12.5)]
    assert dates[0]["starts_at"] == "2026-06-14T10:00:00Z"


async def test_list_is_newest_first(client, conn):
    await in_space(client, conn)
    await client.post("/api/dates", json={**PICNIC, "title": "Old", "starts_at": "2025-01-01T18:00:00Z"})
    await client.post("/api/dates", json={**PICNIC, "title": "New", "starts_at": "2026-09-01T18:00:00Z"})

    assert [d["title"] for d in (await client.get("/api/dates")).json()] == ["New", "Old"]


async def test_date_detail_and_edit(client, conn):
    await in_space(client, conn)
    date_id = (await client.post("/api/dates", json=PICNIC)).json()["id"]

    res = await client.put(f"/api/dates/{date_id}", json={**PICNIC, "title": "Weekend in Bled",
                                                         "ends_at": "2026-06-15T18:00:00+02:00"})

    assert res.status_code == 200, res.text
    detail = (await client.get(f"/api/dates/{date_id}")).json()
    assert (detail["title"], detail["ends_at"]) == ("Weekend in Bled", "2026-06-15T16:00:00Z")


async def test_trip_cannot_end_before_it_starts_and_cost_is_not_negative(client, conn):
    await in_space(client, conn)

    backwards = await client.post("/api/dates", json={**PICNIC, "ends_at": "2026-06-13T12:00:00+02:00"})
    negative = await client.post("/api/dates", json={**PICNIC, "cost": -1})

    assert backwards.json() == {"code": "validation.invalid", "fields": ["ends_at"]}
    assert negative.json() == {"code": "validation.invalid", "fields": ["cost"]}


async def test_other_spaces_dates_are_invisible(client, conn):
    _, _, ana_device = await in_space(client, conn, "Ana")
    date_id = (await client.post("/api/dates", json=PICNIC)).json()["id"]
    await in_space(client, conn, "Bor")

    assert (await client.get("/api/dates")).json() == []
    assert (await client.get(f"/api/dates/{date_id}")).status_code == 404
    assert (await client.put(f"/api/dates/{date_id}", json=PICNIC)).status_code == 404
    assert (await client.delete(f"/api/dates/{date_id}")).status_code == 404
    await login(client, ana_device)
    assert (await client.get(f"/api/dates/{date_id}")).json()["title"] == "Picnic at Bled"


async def test_date_link_works_from_another_active_space(client, conn):
    ana_id, _, _ = await in_space(client, conn, "Ana")
    date_id = (await client.post("/api/dates", json=PICNIC)).json()["id"]
    family = await conn.fetchval("INSERT INTO spaces (name) VALUES ('Family') RETURNING id")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", family, ana_id)
    client.headers["X-Space-Id"] = str(family)

    assert (await client.get(f"/api/dates/{date_id}")).status_code == 200
    assert (await client.get("/api/dates")).json() == []


async def test_deleted_date_disappears(client, conn):
    await in_space(client, conn)
    date_id = (await client.post("/api/dates", json=PICNIC)).json()["id"]

    assert (await client.delete(f"/api/dates/{date_id}")).status_code == 200

    assert (await client.get("/api/dates")).json() == []
    assert (await client.get(f"/api/dates/{date_id}")).status_code == 404


async def test_dates_need_an_active_space(client, conn):
    await signup(client, conn, "Ana")

    assert (await client.get("/api/dates")).status_code == 422
