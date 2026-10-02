from app import config
from tests.fake_authenticator import FakeAuthenticator
from tests.helpers import login, register, signup


async def test_sessions_list_marks_the_current_one(client, conn):
    _, device = await signup(client, conn, "Ana")
    client.cookies.clear()
    await login(client, device)

    sessions = (await client.get("/api/me/sessions")).json()

    assert len(sessions) == 2
    assert [s["current"] for s in sessions].count(True) == 1


async def test_revoked_session_is_logged_out(client, conn):
    _, device = await signup(client, conn, "Ana")
    first_cookie = client.cookies.get("sid")
    client.cookies.clear()
    await login(client, device)
    other = next(s for s in (await client.get("/api/me/sessions")).json() if not s["current"])

    assert (await client.delete(f"/api/me/sessions/{other['id']}")).status_code == 200

    client.cookies.set("sid", first_cookie)
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_revoke_others_keeps_only_the_current_session(client, conn):
    _, device = await signup(client, conn, "Ana")
    client.cookies.clear()
    await login(client, device)

    await client.post("/api/me/sessions/revoke-others")

    sessions = (await client.get("/api/me/sessions")).json()
    assert [s["current"] for s in sessions] == [True]


async def test_cannot_revoke_someone_elses_session(client, conn):
    await signup(client, conn, "Bor")
    bor_session = (await client.get("/api/me/sessions")).json()[0]["id"]
    await signup(client, conn, "Ana")

    assert (await client.delete(f"/api/me/sessions/{bor_session}")).status_code == 404


async def test_recovery_link_registers_a_new_passkey_for_the_same_user(client, conn):
    bor_id, _ = await signup(client, conn, "Bor")
    await signup(client, conn, "Ana", roles=["admin"])
    url = (await client.post(f"/api/admin/users/{bor_id}/recovery-link")).json()["url"]
    assert "/recover/" in url
    client.cookies.clear()

    new_phone = FakeAuthenticator(config.ORIGIN, config.RP_ID)
    res, _ = await register(client, url.rsplit("/", 1)[1], new_phone)
    client.cookies.clear()

    assert res.json()["id"] == bor_id
    assert (await login(client, new_phone)).json()["display_name"] == "Bor"


async def test_recovery_link_works_once(client, conn):
    bor_id, _ = await signup(client, conn, "Bor")
    await signup(client, conn, "Ana", roles=["admin"])
    token = (await client.post(f"/api/admin/users/{bor_id}/recovery-link")).json()["url"].rsplit("/", 1)[1]
    await register(client, token)

    res = await client.post("/api/auth/passkey/register/options", json={"token": token})

    assert res.json() == {"code": "auth.invalid_token"}


async def test_only_admins_create_recovery_links(client, conn):
    bor_id, _ = await signup(client, conn, "Bor")

    assert (await client.post(f"/api/admin/users/{bor_id}/recovery-link")).status_code == 403
