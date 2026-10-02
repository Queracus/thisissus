from tests.helpers import in_space

PICNIC = {"title": "Picnic", "starts_at": "2026-06-14T12:00:00+02:00"}


async def tag_id(client, key):
    return next(t["id"] for t in (await client.get("/api/tags")).json() if t["starter_key"] == key)


async def test_new_space_comes_with_starter_tags(client, conn):
    await in_space(client, conn)

    keys = {t["starter_key"] for t in (await client.get("/api/tags")).json()}

    assert {"food", "outdoors", "movie", "cheap", "romantic"} <= keys


async def test_custom_tag_is_created_once_case_insensitively(client, conn):
    await in_space(client, conn)

    first = (await client.post("/api/tags", json={"name": "Board games"})).json()
    again = (await client.post("/api/tags", json={"name": "board GAMES"})).json()

    assert first["id"] == again["id"]
    assert first["name"] == "Board games" and first["starter_key"] is None


async def test_tags_are_per_space(client, conn):
    await in_space(client, conn, "Ana")
    await client.post("/api/tags", json={"name": "Secret"})
    await in_space(client, conn, "Bor")

    assert "Secret" not in [t["name"] for t in (await client.get("/api/tags")).json()]


async def test_date_carries_its_tags(client, conn):
    await in_space(client, conn)
    food, cheap = await tag_id(client, "food"), await tag_id(client, "cheap")

    date_id = (await client.post("/api/dates", json={**PICNIC, "tag_ids": [food, cheap]})).json()["id"]
    await client.put(f"/api/dates/{date_id}", json={**PICNIC, "tag_ids": [food]})

    assert [t["starter_key"] for t in (await client.get(f"/api/dates/{date_id}")).json()["tags"]] == ["food"]
    assert [t["starter_key"] for t in (await client.get("/api/dates")).json()[0]["tags"]] == ["food"]


async def test_foreign_tag_cannot_be_attached(client, conn):
    await in_space(client, conn, "Ana")
    foreign = (await client.post("/api/tags", json={"name": "Ana only"})).json()["id"]
    await in_space(client, conn, "Bor")

    res = await client.post("/api/dates", json={**PICNIC, "tag_ids": [foreign]})

    assert res.status_code == 400
    assert res.json() == {"code": "tag.invalid"}
