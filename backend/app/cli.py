"""Admin CLI.
Usage:
  python -m app.cli bootstrap-admin "<display name>"   new admin user + one-time invite link
  python -m app.cli unlock <username>                  clear a PIN lockout
"""
import asyncio
import sys

import asyncpg

from app import config
from app.auth.pin import unlock
from app.auth.roles import grant_role
from app.auth.tokens import hash_token, invite_new_user
from app.migrator import migrate


async def run(cmd: str, arg: str) -> str:
    conn = await asyncpg.connect(config.dsn())
    try:
        await migrate(conn, config.MIGRATIONS_DIR)
        if cmd == "bootstrap-admin":
            token = await invite_new_user(conn, arg)
            await grant_role(conn, await conn.fetchval("SELECT user_id FROM auth_tokens WHERE token_hash = $1", hash_token(token)), "admin")
            return f"{config.ORIGIN}/invite/{token}"
        user_id = await conn.fetchval("SELECT id FROM users WHERE lower(username) = lower($1)", arg)
        if not user_id:
            return f"no user '{arg}'"
        await unlock(conn, user_id)
        return f"unlocked {arg}"
    finally:
        await conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("bootstrap-admin", "unlock"):
        sys.exit(__doc__)
    print(asyncio.run(run(sys.argv[1], sys.argv[2])))
