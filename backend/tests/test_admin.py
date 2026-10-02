from tests.helpers import login, register, signup


async def test_regular_user_cannot_use_admin_endpoints(client, conn):
    await signup(client, conn, "Bor")

    res = await client.get("/api/admin/users")

    assert res.status_code == 403
    assert res.json() == {"code": "auth.forbidden"}


async def test_admin_lists_users_with_roles(client, conn):
    await signup(client, conn, "Bor")
    await signup(client, conn, "Ana", roles=["admin"])

    users = (await client.get("/api/admin/users")).json()

    assert [(u["display_name"], u["roles"]) for u in users] == [("Bor", []), ("Ana", ["admin"])]


async def test_admin_can_make_someone_else_admin(client, conn):
    bor_id, bor_device = await signup(client, conn, "Bor")
    await signup(client, conn, "Ana", roles=["admin"])

    res = await client.put(f"/api/admin/users/{bor_id}/roles", json={"roles": ["admin"]})

    assert res.status_code == 200, res.text
    await login(client, bor_device)
    assert (await client.get("/api/admin/users")).status_code == 200


async def test_last_admin_cannot_drop_admin_role(client, conn):
    ana_id, _ = await signup(client, conn, "Ana", roles=["admin"])

    res = await client.put(f"/api/admin/users/{ana_id}/roles", json={"roles": []})

    assert res.status_code == 409
    assert res.json() == {"code": "admin.last_admin"}


async def test_unknown_role_is_rejected(client, conn):
    ana_id, _ = await signup(client, conn, "Ana", roles=["admin"])

    res = await client.put(f"/api/admin/users/{ana_id}/roles", json={"roles": ["admin", "wizard"]})

    assert res.json() == {"code": "admin.unknown_role"}


async def test_admin_invite_link_registers_a_new_user(client, conn):
    await signup(client, conn, "Ana", roles=["admin"])

    url = (await client.post("/api/admin/invites", json={"display_name": "Mama"})).json()["url"]

    client.cookies.clear()
    res, _ = await register(client, url.rsplit("/", 1)[1])
    assert res.json()["display_name"] == "Mama"


async def test_admin_unlocks_a_locked_pin(client, conn):
    bor_id, _ = await signup(client, conn, "Bor")
    await client.put("/api/me/pin", json={"username": "bor", "pin": "123456"})
    for _ in range(5):
        await client.post("/api/auth/pin/login", json={"username": "bor", "pin": "000000"})
    await conn.execute("DELETE FROM login_throttle WHERE key LIKE 'ip:%'")
    await signup(client, conn, "Ana", roles=["admin"])
    assert [u["locked"] for u in (await client.get("/api/admin/users")).json() if u["id"] == bor_id] == [True]

    assert (await client.post(f"/api/admin/users/{bor_id}/unlock")).status_code == 200

    assert (await client.post("/api/auth/pin/login", json={"username": "bor", "pin": "123456"})).status_code == 200


async def test_roles_list_shows_permissions(client, conn):
    await signup(client, conn, "Ana", roles=["admin"])

    roles = (await client.get("/api/admin/roles")).json()

    assert roles[0]["name"] == "admin" and "manage_users" in roles[0]["permissions"]


async def test_me_includes_permissions(client, conn):
    await signup(client, conn, "Ana", roles=["admin"])

    assert "manage_users" in (await client.get("/api/auth/me")).json()["permissions"]
