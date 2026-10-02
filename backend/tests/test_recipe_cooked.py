from app.reminders import tick
from tests.helpers import in_space, login, signup

RAMEN = {"title": "Ramen", "portions": 2, "ingredients": [{"amount": 200, "unit": "g", "item": "noodles"}], "steps": ["Cook"]}


async def couple(client, conn):
    ana_id, space_id, ana = await in_space(client, conn, "Ana")
    bor_id, bor = await signup(client, conn, "Bor")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, bor_id)
    await login(client, ana)
    return ana, bor, bor_id


async def test_we_cooked_it_logs_a_cook_and_marks_cooked(client, conn):
    await couple(client, conn)
    recipe_id = (await client.post("/api/recipes", json=RAMEN)).json()["id"]

    res = await client.post(f"/api/recipes/{recipe_id}/cooked", json={"log_as_date": False})

    assert res.status_code == 200, res.text
    r = (await client.get(f"/api/recipes/{recipe_id}")).json()
    assert r["status"] == "cooked" and len(r["cooks"]) == 1 and r["cooks"][0]["date_id"] is None


async def test_cooking_can_be_logged_as_a_date(client, conn):
    await couple(client, conn)
    food = next(t["id"] for t in (await client.get("/api/tags")).json() if t["starter_key"] == "food")
    recipe_id = (await client.post("/api/recipes", json={**RAMEN, "tag_ids": [food]})).json()["id"]

    date_id = (await client.post(f"/api/recipes/{recipe_id}/cooked", json={"log_as_date": True})).json()["date_id"]

    date = (await client.get(f"/api/dates/{date_id}")).json()
    assert (date["title"], date["recipe_id"], [t["id"] for t in date["tags"]]) == ("Ramen", recipe_id, [food])
    assert (await client.get(f"/api/recipes/{recipe_id}")).json()["cooks"][0]["date_id"] == date_id


async def test_partners_review_recipes_separately(client, conn):
    ana, bor, _ = await couple(client, conn)
    recipe_id = (await client.post("/api/recipes", json=RAMEN)).json()["id"]
    await client.put(f"/api/recipes/{recipe_id}/review", json={"rating": 5, "comment": "Super"})
    await login(client, bor)
    await client.put(f"/api/recipes/{recipe_id}/review", json={"rating": 3, "comment": "Preslano"})

    r = (await client.get(f"/api/recipes/{recipe_id}")).json()

    assert sorted((x["display_name"], x["rating"], x["comment"]) for x in r["reviews"]) == [("Ana", 5, "Super"), ("Bor", 3, "Preslano")]
    assert r["avg_rating"] == 4.0
    assert (await client.get("/api/recipes")).json()[0]["avg_rating"] == 4.0


async def test_partner_is_notified_about_new_and_cooked_recipes(client, conn):
    ana, bor, _ = await couple(client, conn)
    recipe_id = (await client.post("/api/recipes", json=RAMEN)).json()["id"]
    await client.post(f"/api/recipes/{recipe_id}/cooked", json={"log_as_date": False})

    await login(client, bor)
    items = (await client.get("/api/notifications")).json()["items"]

    assert [(n["kind"], n["payload"]["recipe_id"]) for n in items] == [("recipe.cooked", recipe_id), ("recipe.created", recipe_id)]


async def test_unrated_cooked_recipe_is_reminded_once(client, conn):
    _, _, bor_id = await couple(client, conn)
    recipe_id = (await client.post("/api/recipes", json=RAMEN)).json()["id"]
    await client.post(f"/api/recipes/{recipe_id}/cooked", json={"log_as_date": False})
    await client.put(f"/api/recipes/{recipe_id}/review", json={"rating": 5})
    await conn.execute("UPDATE recipe_cooks SET created_at = now() - interval '4 days'")

    await tick(conn, {})
    await tick(conn, {})

    rows = await conn.fetch("SELECT user_id, payload FROM notifications WHERE kind = 'recipe.rating_missing'")
    assert [(r["user_id"], r["payload"]["recipe_id"]) for r in rows] == [(bor_id, recipe_id)]
