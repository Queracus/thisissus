from tests.helpers import in_space
from tests.media_fixtures import jpeg_bytes

RAMEN = {
    "title": "Ramen", "portions": 2, "prep_minutes": 45, "source_url": "https://example.com/ramen",
    "ingredients": [{"amount": 200, "unit": "g", "item": "noodles"}, {"amount": None, "unit": None, "item": "salt to taste"}],
    "steps": ["Boil water", "Cook noodles 3 min"],
}


async def test_recipe_keeps_ordered_ingredients_and_steps(client, conn):
    await in_space(client, conn)

    res = await client.post("/api/recipes", json=RAMEN)

    assert res.status_code == 200, res.text
    r = (await client.get(f"/api/recipes/{res.json()['id']}")).json()
    assert [(i["amount"], i["unit"], i["item"]) for i in r["ingredients"]] == [(200.0, "g", "noodles"), (None, None, "salt to taste")]
    assert r["steps"] == ["Boil water", "Cook noodles 3 min"]
    assert (r["status"], r["portions"], r["prep_minutes"]) == ("want", 2, 45)


async def test_list_by_status(client, conn):
    await in_space(client, conn)
    await client.post("/api/recipes", json=RAMEN)
    await client.post("/api/recipes", json={**RAMEN, "title": "Pancakes", "status": "cooked"})

    assert [r["title"] for r in (await client.get("/api/recipes?status=want")).json()] == ["Ramen"]
    assert [r["title"] for r in (await client.get("/api/recipes?status=cooked")).json()] == ["Pancakes"]
    assert len((await client.get("/api/recipes")).json()) == 2


async def test_update_replaces_ingredients_and_steps(client, conn):
    await in_space(client, conn)
    recipe_id = (await client.post("/api/recipes", json=RAMEN)).json()["id"]

    await client.put(f"/api/recipes/{recipe_id}", json={**RAMEN, "ingredients": [{"amount": 1, "unit": "kg", "item": "rice"}], "steps": ["Cook"]})

    r = (await client.get(f"/api/recipes/{recipe_id}")).json()
    assert ([i["item"] for i in r["ingredients"]], r["steps"]) == (["rice"], ["Cook"])


async def test_recipe_tags(client, conn):
    await in_space(client, conn)
    food = next(t["id"] for t in (await client.get("/api/tags")).json() if t["starter_key"] == "food")

    recipe_id = (await client.post("/api/recipes", json={**RAMEN, "tag_ids": [food]})).json()["id"]

    assert [t["starter_key"] for t in (await client.get(f"/api/recipes/{recipe_id}")).json()["tags"]] == ["food"]


async def test_validation(client, conn):
    await in_space(client, conn)

    zero = await client.post("/api/recipes", json={**RAMEN, "portions": 0})
    bad_url = await client.post("/api/recipes", json={**RAMEN, "source_url": "ftp://x"})
    no_item = await client.post("/api/recipes", json={**RAMEN, "ingredients": [{"amount": 1, "unit": "g", "item": ""}]})

    assert zero.json()["fields"] == ["portions"]
    assert bad_url.json()["fields"] == ["source_url"]
    assert no_item.json()["code"] == "validation.invalid"


async def test_other_space_cannot_see_recipes(client, conn):
    await in_space(client, conn, "Ana")
    recipe_id = (await client.post("/api/recipes", json=RAMEN)).json()["id"]
    await in_space(client, conn, "Eve")

    assert (await client.get("/api/recipes")).json() == []
    assert (await client.get(f"/api/recipes/{recipe_id}")).status_code == 404


async def test_recipe_trash_and_restore(client, conn):
    await in_space(client, conn)
    recipe_id = (await client.post("/api/recipes", json=RAMEN)).json()["id"]

    await client.delete(f"/api/recipes/{recipe_id}")

    assert (await client.get("/api/recipes")).json() == []
    assert [(i["type"], i["id"]) for i in (await client.get("/api/trash")).json()] == [("recipe", recipe_id)]
    await client.post(f"/api/trash/recipe/{recipe_id}/restore")
    assert len((await client.get("/api/recipes")).json()) == 1


async def test_recipe_photos(client, conn):
    await in_space(client, conn)
    recipe_id = (await client.post("/api/recipes", json=RAMEN)).json()["id"]

    res = await client.post(f"/api/recipes/{recipe_id}/photos", files={"file": ("ramen.jpg", jpeg_bytes(), "image/jpeg")})

    assert res.status_code == 200, res.text
    assert [p["id"] for p in (await client.get(f"/api/recipes/{recipe_id}")).json()["photos"]] == [res.json()["id"]]
    assert (await client.get(f"/api/media/{res.json()['id']}/original")).status_code == 200
