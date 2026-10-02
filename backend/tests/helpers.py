"""Shared test flows through the public API."""
from app import config
from app.auth.roles import grant_role
from app.auth.tokens import invite_new_user
from tests.fake_authenticator import FakeAuthenticator


async def register(client, token, device=None):
    device = device or FakeAuthenticator(config.ORIGIN, config.RP_ID)
    opts = await client.post("/api/auth/passkey/register/options", json={"token": token})
    assert opts.status_code == 200, opts.text
    res = await client.post("/api/auth/passkey/register/verify", json={"token": token, "credential": device.create(opts.json())})
    return res, device


async def login(client, device):
    opts = await client.post("/api/auth/passkey/login/options")
    return await client.post("/api/auth/passkey/login/verify", json={"credential": device.get(opts.json())})


async def signup(client, conn, name, roles=()):
    """Invite + register a user (client ends up logged in as them); returns (user_id, device)."""
    res, device = await register(client, await invite_new_user(conn, name))
    user_id = res.json()["id"]
    for role in roles:
        await grant_role(conn, user_id, role)
    return user_id, device
