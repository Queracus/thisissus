"""Admin CLI.
Usage:
  python -m app.cli bootstrap-admin "<display name>"   new admin user (owner of space 'Midva') + invite link
  python -m app.cli unlock <username>                  clear a PIN lockout
  python -m app.cli vapid-keys                         print new web push keys for .env
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
            user_id = await conn.fetchval("SELECT user_id FROM auth_tokens WHERE token_hash = $1", hash_token(token))
            await grant_role(conn, user_id, "admin")
            space_id = await conn.fetchval("INSERT INTO spaces (name) VALUES ('Midva') RETURNING id")
            await conn.execute("INSERT INTO space_members (space_id, user_id, role) VALUES ($1, $2, 'owner')", space_id, user_id)
            return f"{config.ORIGIN}/invite/{token}"
        user_id = await conn.fetchval("SELECT id FROM users WHERE lower(username) = lower($1)", arg)
        if not user_id:
            return f"no user '{arg}'"
        await unlock(conn, user_id)
        return f"unlocked {arg}"
    finally:
        await conn.close()


if __name__ == "__main__":
    if sys.argv[1:] == ["vapid-keys"]:
        from app.push import generate_vapid_keys
        public, private = generate_vapid_keys()
        sys.exit(print(f"VAPID_PUBLIC_KEY={public}\nVAPID_PRIVATE_KEY={private}"))
    if len(sys.argv) != 3 or sys.argv[1] not in ("bootstrap-admin", "unlock"):
        sys.exit(__doc__)
    print(asyncio.run(run(sys.argv[1], sys.argv[2])))
