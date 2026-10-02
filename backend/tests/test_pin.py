import pytest

from app.auth.pin import unlock
from app.auth.tokens import invite_new_user
from tests.helpers import register


@pytest.fixture
async def ana(client, conn):
    """Registered user 'ana' with PIN 123456, logged out."""
    await register(client, await invite_new_user(conn, "Ana"))
    res = await client.put("/api/me/pin", json={"username": "ana", "pin": "123456"})
    assert res.status_code == 200, res.text
    await client.post("/api/auth/logout")
    client.cookies.clear()


async def pin_login(client, username, pin):
    return await client.post("/api/auth/pin/login", json={"username": username, "pin": pin})


async def test_user_with_pin_can_log_in_with_it(client, ana):
    res = await pin_login(client, "Ana", "123456")  # username is case-insensitive

    assert res.status_code == 200, res.text
    assert (await client.get("/api/auth/me")).json()["display_name"] == "Ana"


async def test_wrong_pin_and_unknown_user_look_the_same(client, ana):
    assert (await pin_login(client, "ana", "000000")).json() == {"code": "auth.pin_invalid"}
    assert (await pin_login(client, "nobody", "123456")).json() == {"code": "auth.pin_invalid"}


async def fail_times(client, username, n):
    for _ in range(n):
        await pin_login(client, username, "000000")


async def expire_locks(conn):
    """Time travel: pretend every lock has run out."""
    await conn.execute("UPDATE login_throttle SET locked_until = now() - interval '1 second'")


async def test_five_wrong_pins_lock_the_account_even_for_the_right_pin(client, conn, ana):
    await fail_times(client, "ana", 5)

    res = await pin_login(client, "ana", "123456")

    assert res.status_code == 429
    assert res.json()["code"] == "auth.pin_locked"
    assert res.json()["retry_after"] == 15 * 60


async def test_repeated_lockouts_escalate_15_60_240_minutes(client, conn, ana):
    waits = []
    for _ in range(4):
        await fail_times(client, "ana", 5)
        waits.append((await pin_login(client, "ana", "123456")).json()["retry_after"])
        await expire_locks(conn)

    assert waits == [15 * 60, 60 * 60, 240 * 60, 240 * 60]


async def test_correct_pin_resets_the_account_counter(client, ana):
    await fail_times(client, "ana", 4)
    assert (await pin_login(client, "ana", "123456")).status_code == 200
    await fail_times(client, "ana", 4)

    assert (await pin_login(client, "ana", "123456")).status_code == 200


async def test_failures_across_accounts_lock_the_ip(client, conn, ana):
    for name in ("x1", "x2", "x3", "x4", "x5"):
        await pin_login(client, name, "000000")

    res = await pin_login(client, "ana", "123456")

    assert res.json()["code"] == "auth.pin_locked"


async def test_unlock_clears_an_account_lock(client, conn, ana):
    await fail_times(client, "ana", 5)
    await conn.execute("DELETE FROM login_throttle WHERE key LIKE 'ip:%'")  # only the account lock remains
    user_id = await conn.fetchval("SELECT id FROM users WHERE username = 'ana'")

    await unlock(conn, user_id)

    assert (await pin_login(client, "ana", "123456")).status_code == 200


async def test_pin_is_stored_hashed(conn, ana):
    stored = await conn.fetchval("SELECT pin_hash FROM users WHERE username = 'ana'")

    assert stored.startswith("$argon2") and "123456" not in stored


async def test_pin_must_be_six_digits_and_username_unique(client, conn, ana):
    await register(client, await invite_new_user(conn, "Bor"))

    bad = await client.put("/api/me/pin", json={"username": "bor", "pin": "12ab"})
    taken = await client.put("/api/me/pin", json={"username": "ANA", "pin": "654321"})

    assert bad.json() == {"code": "validation.invalid", "fields": ["pin"]}
    assert taken.json() == {"code": "auth.username_taken"}
