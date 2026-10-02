from datetime import timedelta

from app import config
from app.auth.tokens import invite_new_user
from tests.fake_authenticator import FakeAuthenticator
from tests.helpers import login, register


async def test_invited_user_registers_passkey_and_is_logged_in(client, conn):
    token = await invite_new_user(conn, "Ana")

    res, _ = await register(client, token)

    assert res.status_code == 200, res.text
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["display_name"] == "Ana"


async def test_invite_token_works_only_once(client, conn):
    token = await invite_new_user(conn, "Ana")
    await register(client, token)

    res = await client.post("/api/auth/passkey/register/options", json={"token": token})

    assert res.status_code == 400
    assert res.json() == {"code": "auth.invalid_token"}


async def test_expired_invite_is_rejected(client, conn):
    token = await invite_new_user(conn, "Ana", ttl=timedelta(seconds=-1))

    res = await client.post("/api/auth/passkey/register/options", json={"token": token})

    assert res.json() == {"code": "auth.invalid_token"}


async def test_registered_passkey_logs_in_from_a_new_browser(client, conn):
    _, device = await register(client, await invite_new_user(conn, "Ana"))
    client.cookies.clear()
    assert (await client.get("/api/auth/me")).status_code == 401

    res = await login(client, device)

    assert res.status_code == 200, res.text
    assert (await client.get("/api/auth/me")).json()["display_name"] == "Ana"


async def test_unknown_passkey_cannot_log_in(client, conn):
    await register(client, await invite_new_user(conn, "Ana"))
    client.cookies.clear()

    res = await login(client, FakeAuthenticator(config.ORIGIN, config.RP_ID))

    assert res.json() == {"code": "auth.passkey_unknown"}


async def test_replayed_login_challenge_is_rejected(client, conn):
    _, device = await register(client, await invite_new_user(conn, "Ana"))
    opts = (await client.post("/api/auth/passkey/login/options")).json()
    assertion = device.get(opts)
    await client.post("/api/auth/passkey/login/verify", json={"credential": assertion})

    res = await client.post("/api/auth/passkey/login/verify", json={"credential": assertion})

    assert res.json() == {"code": "auth.challenge_invalid"}


async def test_logout_invalidates_the_session(client, conn):
    await register(client, await invite_new_user(conn, "Ana"))
    stolen_cookie = client.cookies.get("sid")

    assert (await client.post("/api/auth/logout")).status_code == 200

    client.cookies.set("sid", stolen_cookie)
    assert (await client.get("/api/auth/me")).json() == {"code": "auth.required"}


async def test_mutating_request_from_foreign_origin_is_rejected(client):
    res = await client.post("/api/auth/passkey/login/options", headers={"Origin": "https://evil.example"})

    assert res.status_code == 403
    assert res.json() == {"code": "auth.bad_origin"}


async def test_unknown_token_is_rejected(client):
    res = await client.post("/api/auth/passkey/register/options", json={"token": "nope"})

    assert res.json() == {"code": "auth.invalid_token"}
