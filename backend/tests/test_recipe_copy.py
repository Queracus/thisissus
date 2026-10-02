from tests.helpers import in_space, login, make_space, signup
from tests.media_fixtures import jpeg_bytes, open_image
from tests.test_media import drain_jobs

RAMEN = {"title": "Ramen", "portions": 2, "ingredients": [{"amount": 200, "unit": "g", "item": "noodles"}], "steps": ["Boil", "Eat"]}


async def setup(client, conn):
    """Ana shares her recipes section with Mama; Mama has her own 'Family' space. Client ends as Mama."""
    ana_id, us, ana = await in_space(client, conn, "Ana")
    mama_id, mama = await signup(client, conn, "Mama")
    family = await make_space(conn, mama_id, "Family", members=[ana_id])
    await login(client, ana)
    client.headers["X-Space-Id"] = str(us)
    food = next(t["id"] for t in (await client.get("/api/tags")).json() if t["starter_key"] == "food")
    custom = (await client.post("/api/tags", json={"name": "Japonsko"})).json()["id"]
    recipe_id = (await client.post("/api/recipes", json={**RAMEN, "tag_ids": [food, custom]})).json()["id"]
    await client.post(f"/api/recipes/{recipe_id}/photos", files={"file": ("r.jpg", jpeg_bytes(gps=True), "image/jpeg")})
    await drain_jobs(conn)
    await client.post("/api/shares", json={"scope": "section", "entity_type": "recipe", "target_user_id": mama_id})
    await login(client, mama)
    client.headers["X-Space-Id"] = str(family)
    return ana, recipe_id, family


async def test_sharee_copies_a_recipe_into_her_space(client, conn):
    ana, recipe_id, family = await setup(client, conn)

    res = await client.post(f"/api/recipes/{recipe_id}/copy", json={"target_space_id": family})

    assert res.status_code == 200, res.text
    copy = (await client.get(f"/api/recipes/{res.json()['id']}")).json()
    assert (copy["title"], copy["space_id"], copy["steps"]) == ("Ramen", family, ["Boil", "Eat"])
    assert [i["item"] for i in copy["ingredients"]] == ["noodles"]
    assert sorted(t["starter_key"] or t["name"] for t in copy["tags"]) == ["Japonsko", "food"]
    assert [r["title"] for r in (await client.get("/api/recipes")).json()] == ["Ramen"]


async def test_copy_is_independent_of_the_original(client, conn):
    ana, recipe_id, family = await setup(client, conn)
    copy_id = (await client.post(f"/api/recipes/{recipe_id}/copy", json={"target_space_id": family})).json()["id"]
    copy_photo = (await client.get(f"/api/recipes/{copy_id}")).json()["photos"][0]["id"]

    await login(client, ana)
    await client.put(f"/api/recipes/{recipe_id}", json={**RAMEN, "title": "Changed", "steps": ["New"]})
    await client.delete(f"/api/recipes/{recipe_id}")
    await conn.execute("DELETE FROM recipes WHERE id = $1", recipe_id)  # even a hard delete of the source

    copy = await conn.fetchrow("SELECT title FROM recipes WHERE id = $1", copy_id)
    assert copy["title"] == "Ramen"
    assert await conn.fetchval("SELECT count(*) FROM media_chunks WHERE media_id = $1", copy_photo) > 0


async def test_copied_photo_has_no_location(client, conn):
    ana, recipe_id, family = await setup(client, conn)
    copy_id = (await client.post(f"/api/recipes/{recipe_id}/copy", json={"target_space_id": family})).json()["id"]
    photo = (await client.get(f"/api/recipes/{copy_id}")).json()["photos"][0]

    original = await client.get(f"/api/media/{photo['id']}/original")

    assert original.status_code == 200 and photo["status"] == "ready"
    assert not open_image(original.content).getexif().get_ifd(0x8825)
    assert await conn.fetchval("SELECT exif FROM media WHERE id = $1", photo["id"]) is None


async def test_no_access_or_foreign_target_is_refused(client, conn):
    ana, recipe_id, family = await setup(client, conn)
    eve_id, eve = await signup(client, conn, "Eve")
    eve_space = await make_space(conn, eve_id, "Eve's")

    assert (await client.post(f"/api/recipes/{recipe_id}/copy", json={"target_space_id": eve_space})).status_code == 404
    await login(client, eve)
    assert (await client.post(f"/api/recipes/{recipe_id}/copy", json={"target_space_id": eve_space})).status_code == 404
