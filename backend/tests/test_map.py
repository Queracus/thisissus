from tests.helpers import in_space
from tests.media_fixtures import jpeg_bytes
from tests.test_media import drain_jobs, upload

BLED = {"title": "Bled", "starts_at": "2026-06-14T12:00:00+02:00", "lat": 46.3683, "lon": 14.1146, "place_name": "Bled"}


async def test_map_shows_pinned_dates_of_the_active_space(client, conn):
    await in_space(client, conn)
    pinned = (await client.post("/api/dates", json=BLED)).json()["id"]
    await client.post("/api/dates", json={"title": "No pin", "starts_at": "2026-06-15T12:00:00Z"})

    points = (await client.get("/api/dates/map")).json()

    assert [(p["id"], p["title"], p["lat"], p["lon"], p["thumb_id"]) for p in points] == [(pinned, "Bled", 46.3683, 14.1146, None)]


async def test_map_point_has_first_ready_photo_as_thumb(client, conn):
    await in_space(client, conn)
    date_id = (await client.post("/api/dates", json=BLED)).json()["id"]
    media_id = (await upload(client, date_id, jpeg_bytes())).json()["id"]
    await drain_jobs(conn)

    assert (await client.get("/api/dates/map")).json()[0]["thumb_id"] == media_id


async def test_map_excludes_other_spaces(client, conn):
    await in_space(client, conn, "Ana")
    await client.post("/api/dates", json=BLED)
    await in_space(client, conn, "Bor")

    assert (await client.get("/api/dates/map")).json() == []


async def test_location_is_suggested_from_photo_gps(client, conn):
    await in_space(client, conn)
    date_id = (await client.post("/api/dates", json={"title": "Somewhere", "starts_at": "2026-06-14T12:00:00Z"})).json()["id"]
    assert (await client.get(f"/api/dates/{date_id}/suggested-location")).json() is None
    await upload(client, date_id, jpeg_bytes(gps=True))
    await drain_jobs(conn)

    suggestion = (await client.get(f"/api/dates/{date_id}/suggested-location")).json()

    assert (round(suggestion["lat"], 3), round(suggestion["lon"], 3)) == (46.367, 14.1)
