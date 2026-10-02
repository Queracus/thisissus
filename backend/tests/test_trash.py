from app.trash import purge_expired
from tests.helpers import in_space
from tests.media_fixtures import jpeg_bytes
from tests.test_media import upload

PICNIC = {"title": "Picnic", "starts_at": "2026-06-14T12:00:00+02:00"}


async def date_with_photo(client, conn):
    await in_space(client, conn)
    date_id = (await client.post("/api/dates", json=PICNIC)).json()["id"]
    media_id = (await upload(client, date_id, jpeg_bytes())).json()["id"]
    return date_id, media_id


async def trash(client):
    return [(i["type"], i["id"], i["label"]) for i in (await client.get("/api/trash")).json()]


async def test_deleted_date_goes_to_trash_and_restores_with_photos(client, conn):
    date_id, media_id = await date_with_photo(client, conn)
    await client.delete(f"/api/dates/{date_id}")

    assert await trash(client) == [("date", date_id, "Picnic")]
    assert (await client.post(f"/api/trash/date/{date_id}/restore")).status_code == 200

    assert await trash(client) == []
    assert [p["id"] for p in (await client.get(f"/api/dates/{date_id}")).json()["photos"]] == [media_id]


async def test_removed_photo_goes_to_trash_and_restores(client, conn):
    date_id, media_id = await date_with_photo(client, conn)
    await client.delete(f"/api/dates/{date_id}/photos/{media_id}")

    assert await trash(client) == [("photo", media_id, "Picnic")]
    await client.post(f"/api/trash/photo/{media_id}/restore")

    assert (await client.get(f"/api/media/{media_id}/original")).status_code == 200


async def test_purge_now_deletes_for_good(client, conn):
    date_id, media_id = await date_with_photo(client, conn)
    await client.delete(f"/api/dates/{date_id}")

    assert (await client.delete(f"/api/trash/date/{date_id}")).status_code == 200

    assert await trash(client) == []
    assert await conn.fetchval("SELECT count(*) FROM dates WHERE id = $1", date_id) == 0
    assert await conn.fetchval("SELECT count(*) FROM media_chunks WHERE media_id = $1", media_id) == 0


async def test_purge_job_removes_only_items_older_than_30_days(client, conn):
    old_date, old_media = await date_with_photo(client, conn)
    recent_date = (await client.post("/api/dates", json={**PICNIC, "title": "Recent"})).json()["id"]
    await client.delete(f"/api/dates/{old_date}")
    await client.delete(f"/api/dates/{recent_date}")
    await conn.execute("UPDATE dates SET deleted_at = now() - interval '31 days' WHERE id = $1", old_date)
    await conn.execute("UPDATE dates SET deleted_at = now() - interval '29 days' WHERE id = $1", recent_date)

    await purge_expired(conn, {})

    assert await trash(client) == [("date", recent_date, "Recent")]
    assert await conn.fetchval("SELECT count(*) FROM media WHERE id = $1 OR parent_id = $1", old_media) == 0


async def test_trash_is_per_space(client, conn):
    date_id, _ = await date_with_photo(client, conn)
    await client.delete(f"/api/dates/{date_id}")
    await in_space(client, conn, "Bor")

    assert await trash(client) == []
    assert (await client.post(f"/api/trash/date/{date_id}/restore")).status_code == 404
    assert (await client.delete(f"/api/trash/date/{date_id}")).status_code == 404


async def test_unknown_trash_type_is_404(client, conn):
    await in_space(client, conn)

    assert (await client.post("/api/trash/spaceship/1/restore")).status_code == 404
