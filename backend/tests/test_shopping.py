import pytest

from app.recipes_tools import scale
from tests.helpers import in_space

PANCAKES = {"title": "Palačinke", "portions": 2, "ingredients": [
    {"amount": 250, "unit": "g", "item": "moke"}, {"amount": 0.5, "unit": "l", "item": "mleka"},
    {"amount": 1, "unit": None, "item": "jajce"}, {"amount": None, "unit": None, "item": "sol po okusu"}]}


@pytest.mark.parametrize("amount, factor, expected", [
    (250, 1.5, 375), (0.5, 3, 1.5), (1, 1 / 3, 0.33), (2, 1.25, 2.5), (125, 1 / 3, 42), (None, 2, None),
])
def test_scale_rounds_sensibly(amount, factor, expected):
    out = scale([{"amount": amount, "unit": "g", "item": "x"}], 1, factor)
    assert out[0]["amount"] == expected


def test_scale_keeps_unit_and_item():
    assert scale([{"amount": 2, "unit": "dl", "item": "smetane"}], 2, 4) == [{"amount": 4, "unit": "dl", "item": "smetane"}]


async def test_recipe_can_be_viewed_for_more_portions(client, conn):
    await in_space(client, conn)
    recipe_id = (await client.post("/api/recipes", json=PANCAKES)).json()["id"]

    r = (await client.get(f"/api/recipes/{recipe_id}?portions=6")).json()

    assert r["portions"] == 6
    assert [i["amount"] for i in r["ingredients"]] == [750, 1.5, 3, None]


async def test_add_recipe_to_shopping_list_merges_same_items(client, conn):
    await in_space(client, conn)
    recipe_id = (await client.post("/api/recipes", json=PANCAKES)).json()["id"]
    await client.post("/api/shopping", json={"item": "Moke", "amount": 100, "unit": "g"})

    await client.post("/api/shopping/from-recipe", json={"recipe_id": recipe_id, "portions": 4})

    items = {(i["item"].lower(), i["unit"]): i["amount"] for i in (await client.get("/api/shopping")).json()}
    assert items == {("moke", "g"): 600, ("mleka", "l"): 1, ("jajce", None): 2, ("sol po okusu", None): None}


async def test_tick_off_and_clear(client, conn):
    await in_space(client, conn)
    a = (await client.post("/api/shopping", json={"item": "kruh"})).json()["id"]
    await client.post("/api/shopping", json={"item": "mleko"})

    await client.patch(f"/api/shopping/{a}", json={"checked": True})
    listed = (await client.get("/api/shopping")).json()
    assert [(i["item"], i["checked"]) for i in listed] == [("mleko", False), ("kruh", True)]

    await client.post("/api/shopping/clear-checked")
    assert [i["item"] for i in (await client.get("/api/shopping")).json()] == ["mleko"]


async def test_checked_items_are_not_merged_into(client, conn):
    await in_space(client, conn)
    a = (await client.post("/api/shopping", json={"item": "moke", "amount": 100, "unit": "g"})).json()["id"]
    await client.patch(f"/api/shopping/{a}", json={"checked": True})

    await client.post("/api/shopping", json={"item": "moke", "amount": 200, "unit": "g"})

    assert sorted(i["amount"] for i in (await client.get("/api/shopping")).json()) == [100, 200]


async def test_shopping_list_is_per_space(client, conn):
    await in_space(client, conn, "Ana")
    item_id = (await client.post("/api/shopping", json={"item": "kruh"})).json()["id"]
    await in_space(client, conn, "Eve")

    assert (await client.get("/api/shopping")).json() == []
    assert (await client.patch(f"/api/shopping/{item_id}", json={"checked": True})).status_code == 404
