import json

import pytest

from app import recipe_import
from app.recipe_import import iso_minutes, parse_ingredient, parse_recipe_html
from tests.helpers import in_space


def page(data) -> str:
    return f"""<html><head><title>x</title><script type="application/ld+json">{json.dumps(data)}</script></head><body>hi</body></html>"""


RECIPE = {
    "@context": "https://schema.org", "@type": "Recipe", "name": "Palačinke",
    "recipeYield": ["4", "4 porcije"], "prepTime": "PT10M", "cookTime": "PT20M",
    "recipeIngredient": ["250 g moke", "½ l mleka", "2 jajci", "1,5 žlice sladkorja", "sol po okusu"],
    "recipeInstructions": [{"@type": "HowToStep", "text": "Zmešaj vse."}, {"@type": "HowToStep", "text": "Peci."}],
    "image": ["https://example.com/pancakes.jpg"],
}


def test_parses_a_plain_jsonld_recipe():
    draft = parse_recipe_html(page(RECIPE), "https://example.com/r")

    assert (draft["title"], draft["portions"], draft["prep_minutes"]) == ("Palačinke", 4, 30)
    assert draft["ingredients"][:2] == [{"amount": 250.0, "unit": "g", "item": "moke"}, {"amount": 0.5, "unit": "l", "item": "mleka"}]
    assert draft["ingredients"][-1] == {"amount": None, "unit": None, "item": "sol po okusu"}
    assert draft["steps"] == ["Zmešaj vse.", "Peci."]
    assert (draft["source_url"], draft["image_url"]) == ("https://example.com/r", "https://example.com/pancakes.jpg")


def test_finds_the_recipe_inside_a_graph_and_sections():
    graph = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "name": "page"},
        {"@type": ["Recipe", "Thing"], "name": "Ramen", "totalTime": "PT1H5M", "recipeYield": "2 servings",
         "recipeInstructions": [{"@type": "HowToSection", "name": "Broth", "itemListElement": [{"@type": "HowToStep", "text": "Boil"}]},
                                "Serve hot"]},
    ]}

    draft = parse_recipe_html(page(graph), "https://e.com/ramen")

    assert (draft["title"], draft["portions"], draft["prep_minutes"], draft["steps"]) == ("Ramen", 2, 65, ["Boil", "Serve hot"])


def test_page_without_recipe_returns_none():
    assert parse_recipe_html("<html><body>No recipe here</body></html>", "https://e.com") is None
    assert parse_recipe_html(page({"@type": "Article", "name": "News"}), "https://e.com") is None


@pytest.mark.parametrize("text, expected", [
    ("2 jajci", (2.0, None, "jajci")),
    ("1/2 cup sugar", (0.5, "cup", "sugar")),
    ("1 1/2 tbsp oil", (1.5, "tbsp", "oil")),
    ("3 dl smetane", (3.0, "dl", "smetane")),
    ("ščep soli", (None, None, "ščep soli")),
])
def test_ingredient_strings(text, expected):
    i = parse_ingredient(text)
    assert (i["amount"], i["unit"], i["item"]) == expected


def test_iso_durations():
    assert (iso_minutes("PT45M"), iso_minutes("PT2H"), iso_minutes("P0DT1H30M"), iso_minutes("garbage")) == (45, 120, 90, None)


async def test_import_endpoint_returns_an_unsaved_draft(client, conn, monkeypatch):
    await in_space(client, conn)

    async def fake_fetch(url):
        return page(RECIPE)
    monkeypatch.setattr(recipe_import, "fetch_html", fake_fetch)

    res = await client.post("/api/recipes/import", json={"url": "https://example.com/r"})

    assert res.status_code == 200, res.text
    assert res.json()["title"] == "Palačinke"
    assert (await client.get("/api/recipes")).json() == []  # nothing saved yet


async def test_import_without_recipe_data_fails_cleanly(client, conn, monkeypatch):
    await in_space(client, conn)

    async def fake_fetch(url):
        return "<html>nothing</html>"
    monkeypatch.setattr(recipe_import, "fetch_html", fake_fetch)

    res = await client.post("/api/recipes/import", json={"url": "https://example.com/blog"})

    assert (res.status_code, res.json()) == (422, {"code": "recipe.import_failed"})


@pytest.mark.parametrize("url", ["http://127.0.0.1/admin", "http://localhost:8000/api/health", "http://192.168.1.1/", "http://[::1]/"])
async def test_private_addresses_are_never_fetched(url):
    with pytest.raises(recipe_import.ImportBlocked):
        await recipe_import.fetch_html(url)


async def test_imported_image_is_downloaded_into_the_recipe(client, conn, monkeypatch):
    from tests.media_fixtures import jpeg_bytes
    await in_space(client, conn)
    recipe_id = (await client.post("/api/recipes", json={"title": "Palačinke"})).json()["id"]

    async def fake_fetch_bytes(url, max_bytes=None):
        return jpeg_bytes()
    monkeypatch.setattr(recipe_import, "fetch_bytes", fake_fetch_bytes)

    res = await client.post(f"/api/recipes/{recipe_id}/photos/from-url", json={"url": "https://example.com/p.jpg"})

    assert res.status_code == 200, res.text
    assert [p["id"] for p in (await client.get(f"/api/recipes/{recipe_id}")).json()["photos"]] == [res.json()["id"]]


async def test_image_url_on_private_network_is_refused(client, conn):
    await in_space(client, conn)
    recipe_id = (await client.post("/api/recipes", json={"title": "X"})).json()["id"]

    res = await client.post(f"/api/recipes/{recipe_id}/photos/from-url", json={"url": "http://127.0.0.1/secret.jpg"})

    assert res.json() == {"code": "recipe.url_not_allowed"}
