from tests.helpers import in_space, login, signup


async def setup(client, conn):
    """Ana + Bor share a space with three dates; client ends logged in as Ana."""
    ana_id, space_id, ana = await in_space(client, conn, "Ana")
    bor_id, bor = await signup(client, conn, "Bor")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, bor_id)
    await login(client, ana)
    tags = {t["starter_key"]: t["id"] for t in (await client.get("/api/tags")).json()}

    async def date(title, when, cost, tag_keys, place=None):
        body = {"title": title, "starts_at": when, "cost": cost, "place_name": place, "tag_ids": [tags[k] for k in tag_keys]}
        return (await client.post("/api/dates", json=body)).json()["id"]

    ids = {
        "picnic": await date("Picnic", "2026-06-14T12:00:00Z", 10, ["food", "outdoors", "cheap"], "Bled"),
        "opera": await date("Opera night", "2026-03-01T19:00:00Z", 120, ["culture", "romantic"], "Ljubljana"),
        "hike": await date("Hike", "2025-09-10T08:00:00Z", 0, ["outdoors", "cheap"], "Triglav"),
    }
    for who, device, reviews in (("Ana", ana, {"picnic": (5, "yes"), "opera": (4, "yes"), "hike": (3, "maybe")}),
                                 ("Bor", bor, {"picnic": (4, "yes"), "opera": (2, "no")})):
        await login(client, device)
        for key, (rating, again) in reviews.items():
            await client.put(f"/api/dates/{ids[key]}/review", json={"rating": rating, "again": again, "notes": f"{who} loved {key}"})
    await login(client, ana)
    return ids, tags


async def titles(client, query):
    return [d["title"] for d in (await client.get(f"/api/dates?{query}")).json()]


async def test_filter_by_tags_requires_all(client, conn):
    _, tags = await setup(client, conn)

    assert await titles(client, f"tag={tags['outdoors']}") == ["Picnic", "Hike"]
    assert await titles(client, f"tag={tags['outdoors']}&tag={tags['food']}") == ["Picnic"]


async def test_filter_by_minimum_average_rating(client, conn):
    await setup(client, conn)

    assert await titles(client, "min_rating=4") == ["Picnic"]


async def test_both_said_yes(client, conn):
    await setup(client, conn)

    assert await titles(client, "both_yes=true") == ["Picnic"]


async def test_max_cost_and_period(client, conn):
    await setup(client, conn)

    assert await titles(client, "max_cost=10") == ["Picnic", "Hike"]
    assert await titles(client, "from=2026-01-01T00:00:00Z&to=2026-12-31T23:59:59Z") == ["Picnic", "Opera night"]


async def test_text_search_covers_title_place_and_notes(client, conn):
    await setup(client, conn)

    assert await titles(client, "q=ljubljana") == ["Opera night"]
    assert await titles(client, "q=OPERA") == ["Opera night"]
    assert await titles(client, "q=loved%20hike") == ["Hike"]


async def test_filters_combine(client, conn):
    _, tags = await setup(client, conn)

    assert await titles(client, f"tag={tags['cheap']}&min_rating=4&max_cost=50") == ["Picnic"]
