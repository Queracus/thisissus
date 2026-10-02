from tests.helpers import in_space, login, make_space, signup
from tests.media_fixtures import jpeg_bytes
from tests.test_media import drain_jobs


async def world(client, conn):
    """Ana+Bor share 'Us' (a date with a photo, two recipes); Mama shares a 'Family' space with Ana; Eve is a stranger.
    Client ends logged in as Ana with 'Us' active."""
    ana_id, us, ana = await in_space(client, conn, "Ana")
    bor_id, bor = await signup(client, conn, "Bor")
    mama_id, mama = await signup(client, conn, "Mama")
    eve_id, eve = await signup(client, conn, "Eve")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", us, bor_id)
    await make_space(conn, mama_id, "Family", members=[ana_id])
    await login(client, ana)
    date_id = (await client.post("/api/dates", json={"title": "Bled", "starts_at": "2026-06-14T12:00:00Z", "place_name": "Bled"})).json()["id"]
    await client.put(f"/api/dates/{date_id}/review", json={"rating": 5, "again": "yes", "notes": "private feelings"})
    media_id = (await client.post(f"/api/dates/{date_id}/photos", files={"file": ("a.jpg", jpeg_bytes(gps=True), "image/jpeg")})).json()["id"]
    await drain_jobs(conn)
    r1 = (await client.post("/api/recipes", json={"title": "Ramen"})).json()["id"]
    r2 = (await client.post("/api/recipes", json={"title": "Pancakes"})).json()["id"]
    return {"ana": ana, "bor": bor, "mama": mama, "eve": eve, "mama_id": mama_id, "eve_id": eve_id,
            "date": date_id, "media": media_id, "recipes": (r1, r2)}


async def share(client, **body):
    return await client.post("/api/shares", json=body)


async def test_item_share_lets_only_the_target_view(client, conn):
    w = await world(client, conn)
    assert (await share(client, scope="item", entity_type="date", entity_id=w["date"], target_user_id=w["mama_id"])).status_code == 200

    await login(client, w["mama"])
    view = await client.get(f"/api/shared/date/{w['date']}")
    assert view.status_code == 200
    assert (view.json()["title"], view.json()["shared_by_name"]) == ("Bled", "Ana")
    assert "reviews" not in view.json() and "private feelings" not in view.text
    await login(client, w["eve"])
    assert (await client.get(f"/api/shared/date/{w['date']}")).status_code == 404


async def test_section_share_covers_every_recipe_but_nothing_else(client, conn):
    w = await world(client, conn)
    await share(client, scope="section", entity_type="recipe", target_user_id=w["mama_id"])

    await login(client, w["mama"])
    mine = (await client.get("/api/shared-with-me")).json()

    assert sorted((i["type"], i["title"]) for i in mine) == [("recipe", "Pancakes"), ("recipe", "Ramen")]
    assert (await client.get(f"/api/shared/recipe/{w['recipes'][0]}")).status_code == 200
    assert (await client.get(f"/api/shared/date/{w['date']}")).status_code == 404


async def test_revoked_share_stops_working(client, conn):
    w = await world(client, conn)
    share_id = (await share(client, scope="item", entity_type="date", entity_id=w["date"], target_user_id=w["mama_id"])).json()["id"]
    await login(client, w["bor"])  # the partner can revoke too
    assert (await client.delete(f"/api/shares/{share_id}")).status_code == 200

    await login(client, w["mama"])
    assert (await client.get(f"/api/shared/date/{w['date']}")).status_code == 404
    assert (await client.get("/api/shared-with-me")).json() == []


async def test_shares_never_allow_writes(client, conn):
    w = await world(client, conn)
    await share(client, scope="item", entity_type="date", entity_id=w["date"], target_user_id=w["mama_id"])
    await login(client, w["mama"])

    assert (await client.put(f"/api/dates/{w['date']}", json={"title": "x", "starts_at": "2026-06-14T12:00:00Z"})).status_code == 404
    assert (await client.delete(f"/api/dates/{w['date']}")).status_code == 404
    assert (await client.get(f"/api/dates/{w['date']}")).status_code == 404  # member view stays members-only


async def test_shared_media_is_derivatives_only(client, conn):
    w = await world(client, conn)
    await share(client, scope="item", entity_type="date", entity_id=w["date"], target_user_id=w["mama_id"])
    await login(client, w["mama"])

    assert (await client.get(f"/api/media/{w['media']}/display")).status_code == 200
    assert (await client.get(f"/api/media/{w['media']}/thumb")).status_code == 200
    assert (await client.get(f"/api/media/{w['media']}/original")).status_code == 404
    photos = (await client.get(f"/api/shared/date/{w['date']}")).json()["photos"]
    assert [p["id"] for p in photos] == [w["media"]]
    await login(client, w["eve"])
    assert (await client.get(f"/api/media/{w['media']}/display")).status_code == 404


async def test_only_members_share_and_only_to_contacts(client, conn):
    w = await world(client, conn)
    to_stranger = await share(client, scope="item", entity_type="date", entity_id=w["date"], target_user_id=w["eve_id"])
    await login(client, w["eve"])
    outsider = await share(client, scope="item", entity_type="date", entity_id=w["date"], target_user_id=w["eve_id"])

    assert to_stranger.json() == {"code": "share.not_a_contact"}
    assert outsider.status_code == 404


async def test_item_badges_and_space_share_list(client, conn):
    w = await world(client, conn)
    await share(client, scope="item", entity_type="date", entity_id=w["date"], target_user_id=w["mama_id"])
    await share(client, scope="section", entity_type="recipe", target_user_id=w["mama_id"])

    badges = (await client.get(f"/api/shares?entity_type=date&entity_id={w['date']}")).json()
    everything = (await client.get("/api/shares")).json()

    assert [(b["target_name"], b["created_by_name"]) for b in badges] == [("Mama", "Ana")]
    assert sorted((s["scope"], s["entity_type"]) for s in everything) == [("item", "date"), ("section", "recipe")]


async def test_contacts_are_people_i_share_a_space_with(client, conn):
    w = await world(client, conn)

    names = sorted(c["display_name"] for c in (await client.get("/api/shares/contacts")).json())

    assert names == ["Bor", "Mama"]
