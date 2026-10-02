import pathlib

import asyncpg

LOCK_ID = 424242  # advisory lock: API and worker never migrate at the same time


async def migrate(conn: asyncpg.Connection, folder: pathlib.Path) -> list[str]:
    """Apply new NNN_name.sql files from folder in order, one transaction per file; return the versions applied."""
    await conn.execute("SELECT pg_advisory_lock($1)", LOCK_ID)
    try:
        await conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
        done = {r["version"] for r in await conn.fetch("SELECT version FROM schema_migrations")}
        applied = []
        for f in sorted(folder.glob("*.sql")):
            if f.stem in done:
                continue
            async with conn.transaction():
                await conn.execute(f.read_text(encoding="utf-8"))
                await conn.execute("INSERT INTO schema_migrations(version) VALUES ($1)", f.stem)
            applied.append(f.stem)
        return applied
    finally:
        await conn.execute("SELECT pg_advisory_unlock($1)", LOCK_ID)
