"""Admin CLI. Usage: python -m app.cli bootstrap-admin <display name>"""
import asyncio
import sys

import asyncpg

from app import config
from app.auth.tokens import invite_new_user
from app.migrator import migrate


async def bootstrap_admin(name: str) -> str:
    conn = await asyncpg.connect(config.dsn())
    try:
        await migrate(conn, config.MIGRATIONS_DIR)
        return f"{config.ORIGIN}/invite/{await invite_new_user(conn, name)}"
    finally:
        await conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "bootstrap-admin":
        sys.exit(__doc__)
    print(asyncio.run(bootstrap_admin(sys.argv[2])))
