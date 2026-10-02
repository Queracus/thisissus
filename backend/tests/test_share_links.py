from tests.helpers import in_space, signup
from tests.media_fixtures import jpeg_bytes
from tests.test_media import drain_jobs


async def date_with_photo(client, conn):
    await in_space(client, conn)
    date_id = (await client.post("/api/dates", json={"title": "Bled", "starts_at": "2026-06-14T12:00:00Z"})).json()["id"]
    media_id = (await client.post(f"/api/dates/{date_id}/photos", files={"file": ("a.jpg", jpeg_bytes(gps=True), "image/jpeg")})).json()["id"]
    await drain_jobs(conn)
    return date_id, media_id


async def link(client, **body):
    res = await client.post("/api/shares/links", json=body)
    assert res.status_code == 200, res.text
    return res.json()["url"].rsplit("/", 1)[1], res.json()


async def test_link_shows_the_item_without_an_account(client, conn):
    date_id, media_id = await date_with_photo(client, conn)
    token, created = await link(client, scope="item", entity_type="date", entity_id=date_id, expires_in="1d")
    client.cookies.clear()

    res = await client.get(f"/api/s/{token}")

    assert res.status_code == 200, res.text
    assert (res.json()["title"], res.json()["type"]) == ("Bled", "date")
    assert res.headers["x-robots-tag"] == "noindex, nofollow"
    assert "/s/" in created["url"] and created["expires_at"]


async def test_link_media_is_derivatives_of_covered_items_only(client, conn):
    date_id, media_id = await date_with_photo(client, conn)
    other_date = (await client.post("/api/dates", json={"title": "Secret", "starts_at": "2026-06-15T12:00:00Z"})).json()["id"]
    other_media = (await client.post(f"/api/dates/{other_date}/photos", files={"file": ("b.jpg", jpeg_bytes(), "image/jpeg")})).json()["id"]
    await drain_jobs(conn)
    token, _ = await link(client, scope="item", entity_type="date", entity_id=date_id, expires_in="1h")
    client.cookies.clear()

    assert (await client.get(f"/api/s/{token}/media/{media_id}/display")).status_code == 200
    assert (await client.get(f"/api/s/{token}/media/{media_id}/original")).status_code == 404
    assert (await client.get(f"/api/s/{token}/media/{other_media}/display")).status_code == 404


async def test_expired_and_revoked_links_stop_working(client, conn):
    date_id, _ = await date_with_photo(client, conn)
    expired, _ = await link(client, scope="item", entity_type="date", entity_id=date_id, expires_in="1w")
    revoked, created = await link(client, scope="item", entity_type="date", entity_id=date_id, expires_in="1w")
    await conn.execute("UPDATE shares SET expires_at = now() - interval '1 second' WHERE token_hash = sha256($1::bytea)", expired.encode())
    await client.delete(f"/api/shares/{created['id']}")
    client.cookies.clear()

    assert (await client.get(f"/api/s/{expired}")).status_code == 404
    assert (await client.get(f"/api/s/{revoked}")).status_code == 404
    assert (await client.get("/api/s/not-a-real-token")).status_code == 404


async def test_token_is_stored_hashed(client, conn):
    date_id, _ = await date_with_photo(client, conn)
    token, _ = await link(client, scope="item", entity_type="date", entity_id=date_id, expires_in="1d")

    stored = await conn.fetchval("SELECT token_hash FROM shares WHERE token_hash IS NOT NULL")

    assert token.encode() not in stored and len(stored) == 32


async def test_section_link_lists_and_opens_only_that_section(client, conn):
    date_id, _ = await date_with_photo(client, conn)
    recipe_id = (await client.post("/api/recipes", json={"title": "Ramen"})).json()["id"]
    token, _ = await link(client, scope="section", entity_type="recipe", expires_in="1w")
    client.cookies.clear()

    section = (await client.get(f"/api/s/{token}")).json()

    assert (section["type"], [i["title"] for i in section["items"]]) == ("section", ["Ramen"])
    assert (await client.get(f"/api/s/{token}/recipe/{recipe_id}")).json()["title"] == "Ramen"
    assert (await client.get(f"/api/s/{token}/date/{date_id}")).status_code == 404


async def test_expiry_must_be_one_of_the_choices_and_only_members_create(client, conn):
    date_id, _ = await date_with_photo(client, conn)

    forever = await client.post("/api/shares/links", json={"scope": "item", "entity_type": "date", "entity_id": date_id, "expires_in": "forever"})
    await signup(client, conn, "Eve")
    outsider = await client.post("/api/shares/links", json={"scope": "item", "entity_type": "date", "entity_id": date_id, "expires_in": "1h"})

    assert forever.json()["fields"] == ["expires_in"]
    assert outsider.status_code == 404
