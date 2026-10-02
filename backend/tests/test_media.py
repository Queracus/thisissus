import os

from app.jobs import run_once
from app.media.store import CHUNK_SIZE, read_range, save_bytes
from app.worker import HANDLERS
from tests.helpers import in_space, signup
from tests.media_fixtures import heic_bytes, jpeg_bytes, open_image

PICNIC = {"title": "Picnic", "starts_at": "2026-06-14T12:00:00+02:00"}


async def date_with_space(client, conn):
    user_id, space_id, device = await in_space(client, conn)
    date_id = (await client.post("/api/dates", json=PICNIC)).json()["id"]
    return date_id, space_id, user_id


async def upload(client, date_id, data, name="photo.jpg", mime="image/jpeg"):
    return await client.post(f"/api/dates/{date_id}/photos", files={"file": (name, data, mime)})


async def drain_jobs(conn):
    while await run_once(conn, HANDLERS):
        pass


async def test_uploaded_photo_is_stored_byte_for_byte(client, conn):
    date_id, _, _ = await date_with_space(client, conn)
    data = jpeg_bytes()

    res = await upload(client, date_id, data)

    assert res.status_code == 200, res.text
    photos = (await client.get(f"/api/dates/{date_id}")).json()["photos"]
    assert [(p["id"], p["status"]) for p in photos] == [(res.json()["id"], "pending")]
    original = await client.get(f"/api/media/{photos[0]['id']}/original")
    assert original.content == data
    assert original.headers["cache-control"] == "private, max-age=31536000, immutable"


async def test_range_reads_cross_chunk_boundaries(conn):
    space_id = await conn.fetchval("INSERT INTO spaces (name) VALUES ('x') RETURNING id")
    data = os.urandom(CHUNK_SIZE * 2 + 12345)
    media_id = await save_bytes(conn, space_id, None, "photo", "original", "application/octet-stream", data)

    assert await read_range(conn, media_id, CHUNK_SIZE - 10, CHUNK_SIZE + 10) == data[CHUNK_SIZE - 10:CHUNK_SIZE + 11]
    assert await read_range(conn, media_id, 0, len(data) - 1) == data


async def test_http_range_request_returns_partial_content(client, conn):
    date_id, _, _ = await date_with_space(client, conn)
    data = jpeg_bytes(1600, 1200, noise=True)
    assert len(data) > CHUNK_SIZE
    media_id = (await upload(client, date_id, data)).json()["id"]

    res = await client.get(f"/api/media/{media_id}/original", headers={"Range": f"bytes={CHUNK_SIZE - 5}-{CHUNK_SIZE + 4}"})

    assert res.status_code == 206
    assert res.content == data[CHUNK_SIZE - 5:CHUNK_SIZE + 5]
    assert res.headers["content-range"] == f"bytes {CHUNK_SIZE - 5}-{CHUNK_SIZE + 4}/{len(data)}"


async def test_wrong_type_and_oversize_are_rejected(client, conn, monkeypatch):
    date_id, _, _ = await date_with_space(client, conn)
    monkeypatch.setattr("app.media.store.PHOTO_MAX_BYTES", 1000)

    not_image = await upload(client, date_id, b"hello, I am a text file", "x.jpg", "image/jpeg")
    too_big = await upload(client, date_id, jpeg_bytes())

    assert (not_image.status_code, not_image.json()) == (415, {"code": "media.unsupported_type"})
    assert (too_big.status_code, too_big.json()) == (413, {"code": "media.too_large"})
    assert (await client.get(f"/api/dates/{date_id}")).json()["photos"] == []


async def test_worker_makes_webp_display_and_thumb(client, conn):
    date_id, _, _ = await date_with_space(client, conn)
    media_id = (await upload(client, date_id, jpeg_bytes(3000, 2000))).json()["id"]

    await drain_jobs(conn)

    photo = (await client.get(f"/api/dates/{date_id}")).json()["photos"][0]
    assert (photo["status"], photo["width"], photo["height"]) == ("ready", 3000, 2000)
    display = open_image((await client.get(f"/api/media/{media_id}/display")).content)
    thumb = open_image((await client.get(f"/api/media/{media_id}/thumb")).content)
    assert (display.format, max(display.size)) == ("WEBP", 2048)
    assert (thumb.format, max(thumb.size)) == ("WEBP", 400)


async def test_heic_photos_get_viewable_derivatives(client, conn):
    date_id, _, _ = await date_with_space(client, conn)
    media_id = (await upload(client, date_id, heic_bytes(), "IMG_0001.HEIC", "image/heic")).json()["id"]

    await drain_jobs(conn)

    assert open_image((await client.get(f"/api/media/{media_id}/display")).content).format == "WEBP"


async def test_derivatives_never_carry_gps_but_original_location_is_known(client, conn):
    date_id, _, _ = await date_with_space(client, conn)
    media_id = (await upload(client, date_id, jpeg_bytes(gps=True))).json()["id"]

    await drain_jobs(conn)

    for variant in ("display", "thumb"):
        img = open_image((await client.get(f"/api/media/{media_id}/{variant}")).content)
        assert not img.getexif().get_ifd(0x8825), variant
    exif = await conn.fetchval("SELECT exif FROM media WHERE id = $1", media_id)
    assert (round(exif["lat"], 3), round(exif["lon"], 3)) == (46.367, 14.1)


async def test_non_members_cannot_see_or_add_photos(client, conn):
    date_id, _, _ = await date_with_space(client, conn)
    media_id = (await upload(client, date_id, jpeg_bytes())).json()["id"]
    await signup(client, conn, "Eve")

    assert (await client.get(f"/api/media/{media_id}/original")).status_code == 404
    assert (await upload(client, date_id, jpeg_bytes())).status_code == 404


async def test_caption_and_order(client, conn):
    date_id, _, _ = await date_with_space(client, conn)
    first = (await upload(client, date_id, jpeg_bytes())).json()["id"]
    second = (await upload(client, date_id, jpeg_bytes())).json()["id"]

    await client.patch(f"/api/dates/{date_id}/photos/{first}", json={"caption": "Sunset"})
    await client.put(f"/api/dates/{date_id}/photos/order", json={"media_ids": [second, first]})

    photos = (await client.get(f"/api/dates/{date_id}")).json()["photos"]
    assert [(p["id"], p["caption"]) for p in photos] == [(second, None), (first, "Sunset")]


async def test_removed_photo_disappears(client, conn):
    date_id, _, _ = await date_with_space(client, conn)
    media_id = (await upload(client, date_id, jpeg_bytes())).json()["id"]

    assert (await client.delete(f"/api/dates/{date_id}/photos/{media_id}")).status_code == 200

    assert (await client.get(f"/api/dates/{date_id}")).json()["photos"] == []
    assert (await client.get(f"/api/media/{media_id}/original")).status_code == 404
