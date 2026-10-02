from tests.helpers import login, register, signup


async def create_space(client, name, owner_id):
    res = await client.post("/api/admin/spaces", json={"name": name, "owner_id": owner_id})
    assert res.status_code == 200, res.text
    return res.json()["id"]


async def test_admin_creates_space_and_owner_sees_it(client, conn):
    ana_id, _ = await signup(client, conn, "Ana", roles=["admin"])

    space_id = await create_space(client, "Us", ana_id)

    assert (await client.get("/api/spaces")).json() == [{"id": space_id, "name": "Us", "role": "owner"}]


async def test_only_admins_create_spaces(client, conn):
    bor_id, _ = await signup(client, conn, "Bor")

    res = await client.post("/api/admin/spaces", json={"name": "Us", "owner_id": bor_id})

    assert res.status_code == 403


async def test_non_member_cannot_see_or_select_a_space(client, conn):
    ana_id, _ = await signup(client, conn, "Ana", roles=["admin"])
    space_id = await create_space(client, "Us", ana_id)
    await signup(client, conn, "Bor")

    assert (await client.get("/api/spaces")).json() == []
    res = await client.get("/api/space", headers={"X-Space-Id": str(space_id)})
    assert res.status_code == 404
    assert res.json() == {"code": "space.not_found"}


async def test_member_selects_active_space_by_header(client, conn):
    ana_id, _ = await signup(client, conn, "Ana", roles=["admin"])
    space_id = await create_space(client, "Us", ana_id)

    res = await client.get("/api/space", headers={"X-Space-Id": str(space_id)})

    assert res.json() == {"id": space_id, "name": "Us", "role": "owner"}


async def test_owner_invites_a_new_person_who_joins_on_registration(client, conn):
    ana_id, _ = await signup(client, conn, "Ana", roles=["admin"])
    space_id = await create_space(client, "Us", ana_id)

    url = (await client.post(f"/api/spaces/{space_id}/invites", json={"display_name": "Bor"})).json()["url"]
    client.cookies.clear()
    await register(client, url.rsplit("/", 1)[1])

    assert (await client.get("/api/spaces")).json() == [{"id": space_id, "name": "Us", "role": "member"}]


async def test_owner_invites_an_existing_user_with_a_join_link(client, conn):
    ana_id, ana_device = await signup(client, conn, "Ana", roles=["admin"])
    other_space = await create_space(client, "Ana's family", ana_id)
    space_id = await create_space(client, "Us", ana_id)
    _, bor_device = await signup(client, conn, "Bor")
    await login(client, ana_device)

    url = (await client.post(f"/api/spaces/{space_id}/invites", json={})).json()["url"]
    assert "/join/" in url
    await login(client, bor_device)
    assert (await client.post("/api/spaces/join", json={"token": url.rsplit("/", 1)[1]})).status_code == 200

    assert [s["id"] for s in (await client.get("/api/spaces")).json()] == [space_id]
    assert other_space not in [s["id"] for s in (await client.get("/api/spaces")).json()]


async def test_members_list_and_owner_only_actions(client, conn):
    ana_id, ana_device = await signup(client, conn, "Ana", roles=["admin"])
    space_id = await create_space(client, "Us", ana_id)
    url = (await client.post(f"/api/spaces/{space_id}/invites", json={"display_name": "Bor"})).json()["url"]
    client.cookies.clear()
    await register(client, url.rsplit("/", 1)[1])

    members = (await client.get(f"/api/spaces/{space_id}/members")).json()
    invite = await client.post(f"/api/spaces/{space_id}/invites", json={"display_name": "Mama"})
    rename = await client.patch(f"/api/spaces/{space_id}", json={"name": "Midva"})

    assert [(m["display_name"], m["role"]) for m in members] == [("Ana", "owner"), ("Bor", "member")]
    assert invite.json() == {"code": "space.owner_required"}
    assert rename.json() == {"code": "space.owner_required"}


async def test_owner_renames_space(client, conn):
    ana_id, _ = await signup(client, conn, "Ana", roles=["admin"])
    space_id = await create_space(client, "Us", ana_id)

    await client.patch(f"/api/spaces/{space_id}", json={"name": "Midva 💕"})

    assert (await client.get("/api/spaces")).json()[0]["name"] == "Midva 💕"
