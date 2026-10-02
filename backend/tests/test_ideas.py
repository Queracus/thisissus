from tests.helpers import in_space, login, signup

PICNIC = {"title": "Picnic at Bled", "description": "Bring the red blanket", "url": "https://www.bled.si",
          "est_cost": 20, "season": "summer"}


async def test_new_idea_is_listed_with_who_suggested_it(client, conn):
    await in_space(client, conn, "Ana")

    res = await client.post("/api/ideas", json=PICNIC)

    assert res.status_code == 200, res.text
    ideas = (await client.get("/api/ideas")).json()
    assert [(i["title"], i["status"], i["suggested_by_name"], i["est_cost"], i["season"]) for i in ideas] == [
        ("Picnic at Bled", "idea", "Ana", 20.0, "summer")]


async def test_partner_sees_and_edits_the_idea(client, conn):
    _, space_id, ana = await in_space(client, conn, "Ana")
    idea_id = (await client.post("/api/ideas", json=PICNIC)).json()["id"]
    bor_id, _ = await signup(client, conn, "Bor")
    await conn.execute("INSERT INTO space_members VALUES ($1, $2, 'member')", space_id, bor_id)

    res = await client.put(f"/api/ideas/{idea_id}", json={**PICNIC, "title": "Picnic + swim"})

    assert res.status_code == 200, res.text
    idea = (await client.get(f"/api/ideas/{idea_id}")).json()
    assert (idea["title"], idea["suggested_by_name"]) == ("Picnic + swim", "Ana")


async def test_idea_tags(client, conn):
    await in_space(client, conn)
    outdoors = next(t["id"] for t in (await client.get("/api/tags")).json() if t["starter_key"] == "outdoors")

    idea_id = (await client.post("/api/ideas", json={**PICNIC, "tag_ids": [outdoors]})).json()["id"]

    assert [t["starter_key"] for t in (await client.get(f"/api/ideas/{idea_id}")).json()["tags"]] == ["outdoors"]


async def test_validation(client, conn):
    await in_space(client, conn)

    bad_url = await client.post("/api/ideas", json={**PICNIC, "url": "javascript:alert(1)"})
    bad_season = await client.post("/api/ideas", json={**PICNIC, "season": "monsoon"})
    minimal = await client.post("/api/ideas", json={"title": "Kino"})

    assert bad_url.json()["fields"] == ["url"]
    assert bad_season.json()["fields"] == ["season"]
    assert minimal.status_code == 200


async def test_other_space_cannot_see_ideas(client, conn):
    await in_space(client, conn, "Ana")
    idea_id = (await client.post("/api/ideas", json=PICNIC)).json()["id"]
    await in_space(client, conn, "Eve")

    assert (await client.get("/api/ideas")).json() == []
    assert (await client.get(f"/api/ideas/{idea_id}")).status_code == 404
    assert (await client.delete(f"/api/ideas/{idea_id}")).status_code == 404


async def test_deleted_idea_goes_to_trash(client, conn):
    await in_space(client, conn)
    idea_id = (await client.post("/api/ideas", json=PICNIC)).json()["id"]

    await client.delete(f"/api/ideas/{idea_id}")

    assert (await client.get("/api/ideas")).json() == []
    assert [(i["type"], i["id"]) for i in (await client.get("/api/trash")).json()] == [("idea", idea_id)]
    await client.post(f"/api/trash/idea/{idea_id}/restore")
    assert len((await client.get("/api/ideas")).json()) == 1
