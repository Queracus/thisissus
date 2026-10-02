"""PIN fallback login with per-account and per-IP lockout: 5 failures → 15, then 60, then 240 minutes."""
import asyncpg
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from starlette.concurrency import run_in_threadpool

from app.errors import ApiError

MAX_FAILURES = 5
LOCK_MINUTES = (15, 60, 240)
_hasher = PasswordHasher()


async def set_pin(conn: asyncpg.Connection, user_id: int, username: str, pin: str) -> None:
    pin_hash = await run_in_threadpool(_hasher.hash, pin)  # argon2 is CPU-heavy: keep it off the event loop
    try:
        await conn.execute("UPDATE users SET username = $2, pin_hash = $3 WHERE id = $1", user_id, username, pin_hash)
    except asyncpg.UniqueViolationError:
        raise ApiError(409, "auth.username_taken")


async def _locked_seconds(conn: asyncpg.Connection, keys: list[str]) -> int:
    return await conn.fetchval(
        "SELECT coalesce(ceil(extract(epoch FROM max(locked_until) - now())), 0)::int FROM login_throttle WHERE key = ANY($1::text[]) AND locked_until > now()",
        keys)


async def _fail(conn: asyncpg.Connection, key: str) -> None:
    await conn.execute(
        """INSERT INTO login_throttle AS t (key, failures) VALUES ($1, 1)
           ON CONFLICT (key) DO UPDATE SET failures = t.failures + 1""", key)
    await conn.execute(
        """UPDATE login_throttle SET failures = 0, level = level + 1,
                  locked_until = now() + make_interval(mins => ($2::int[])[least(level + 1, array_length($2::int[], 1))])
           WHERE key = $1 AND failures >= $3""", key, list(LOCK_MINUTES), MAX_FAILURES)


async def check_pin(conn: asyncpg.Connection, username: str, pin: str, ip: str) -> int:
    """Return the user id for a correct PIN; raise auth.pin_locked / auth.pin_invalid otherwise."""
    user = await conn.fetchrow("SELECT id, pin_hash FROM users WHERE lower(username) = lower($1) AND disabled_at IS NULL", username)
    keys = [f"ip:{ip}"] + ([f"user:{user['id']}"] if user else [])
    if seconds := await _locked_seconds(conn, keys):
        raise ApiError(429, "auth.pin_locked", retry_after=seconds)
    try:
        if not (user and user["pin_hash"]):
            raise VerifyMismatchError
        await run_in_threadpool(_hasher.verify, user["pin_hash"], pin)
    except VerifyMismatchError:
        for key in keys:
            await _fail(conn, key)
        raise ApiError(401, "auth.pin_invalid")
    await conn.execute("DELETE FROM login_throttle WHERE key = $1", f"user:{user['id']}")
    await conn.execute("UPDATE login_throttle SET failures = 0 WHERE key = $1", f"ip:{ip}")
    return user["id"]


async def unlock(conn: asyncpg.Connection, user_id: int) -> None:
    await conn.execute("DELETE FROM login_throttle WHERE key = $1", f"user:{user_id}")
