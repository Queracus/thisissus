from tests.helpers import in_space, login, signup

PICNIC = {"title": "Picnic", "starts_at": "2026-06-14T12:00:00+02:00"}


async def couple_with_date(client, conn):
    """Ana and Bor share a space with one date; client is logged in as Ana. Returns (date_id, ana_device, bor_device)."""
    ana_id, space_id, ana_device = await in_space(client, conn, "Ana")
    bor_id, bor_device = await signup(client, conn, "Bor")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, bor_id)
    await login(client, ana_device)
    date_id = (await client.post("/api/dates", json=PICNIC)).json()["id"]
    return date_id, ana_device, bor_device


async def test_partner_reviews_a_date(client, conn):
    date_id, _, _ = await couple_with_date(client, conn)

    res = await client.put(f"/api/dates/{date_id}/review", json={"rating": 5, "again": "yes", "notes": "Best sunset"})

    assert res.status_code == 200, res.text
    detail = (await client.get(f"/api/dates/{date_id}")).json()
    assert [(r["display_name"], r["rating"], r["again"], r["notes"]) for r in detail["reviews"]] == [("Ana", 5, "yes", "Best sunset")]


async def test_both_reviews_shown_with_average(client, conn):
    date_id, _, bor_device = await couple_with_date(client, conn)
    await client.put(f"/api/dates/{date_id}/review", json={"rating": 5, "again": "yes"})
    await login(client, bor_device)

    await client.put(f"/api/dates/{date_id}/review", json={"rating": 2, "again": "maybe", "notes": "Too many bugs"})

    detail = (await client.get(f"/api/dates/{date_id}")).json()
    assert sorted((r["display_name"], r["rating"]) for r in detail["reviews"]) == [("Ana", 5), ("Bor", 2)]
    assert detail["avg_rating"] == 3.5
    assert (await client.get("/api/dates")).json()[0]["avg_rating"] == 3.5


async def test_reviewing_again_replaces_only_my_review(client, conn):
    date_id, _, bor_device = await couple_with_date(client, conn)
    await client.put(f"/api/dates/{date_id}/review", json={"rating": 5, "again": "yes"})
    await login(client, bor_device)
    await client.put(f"/api/dates/{date_id}/review", json={"rating": 2, "again": "no"})

    await client.put(f"/api/dates/{date_id}/review", json={"rating": 4, "again": "maybe"})

    reviews = {r["display_name"]: (r["rating"], r["again"]) for r in (await client.get(f"/api/dates/{date_id}")).json()["reviews"]}
    assert reviews == {"Ana": (5, "yes"), "Bor": (4, "maybe")}


async def test_review_values_are_validated(client, conn):
    date_id, _, _ = await couple_with_date(client, conn)

    too_high = await client.put(f"/api/dates/{date_id}/review", json={"rating": 6, "again": "yes"})
    bad_again = await client.put(f"/api/dates/{date_id}/review", json={"rating": 3, "again": "never"})

    assert too_high.json()["fields"] == ["rating"]
    assert bad_again.json()["fields"] == ["again"]


async def test_non_member_cannot_review(client, conn):
    date_id, _, _ = await couple_with_date(client, conn)
    await signup(client, conn, "Eve")

    assert (await client.put(f"/api/dates/{date_id}/review", json={"rating": 1, "again": "no"})).status_code == 404
