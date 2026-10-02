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


async def make_space(conn, owner_id, name="Us", members=()):
    space_id = await conn.fetchval("INSERT INTO spaces (name) VALUES ($1) RETURNING id", name)
    await conn.execute("INSERT INTO space_members (space_id, user_id, role) VALUES ($1, $2, 'owner')", space_id, owner_id)
    for user_id in members:
        await conn.execute("INSERT INTO space_members (space_id, user_id, role) VALUES ($1, $2, 'member')", space_id, user_id)
    return space_id


async def in_space(client, conn, name="Ana"):
    """Sign up `name`, give them a space and make it the client's active space; returns (user_id, space_id, device)."""
    user_id, device = await signup(client, conn, name)
    space_id = await make_space(conn, user_id)
    client.headers["X-Space-Id"] = str(space_id)
    return user_id, space_id, device


async def signup(client, conn, name, roles=()):
    """Invite + register a user (client ends up logged in as them); returns (user_id, device)."""
    res, device = await register(client, await invite_new_user(conn, name))
    user_id = res.json()["id"]
    for role in roles:
        await grant_role(conn, user_id, role)
    return user_id, device
