import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from app import config
from app.db import get_conn, init_conn
from app.main import app
from app.migrator import migrate


@pytest.fixture(scope="session")
async def test_db():
    """Test database built by the real migrations, gentle on the server:
    - created once, then reset by recreating its schema (no DROP DATABASE every run);
    - autovacuum + vacuum truncation off on every test table. On Windows a vacuum truncate that hits a file
      held by another program (antivirus) makes Postgres PANIC; test data is thrown away anyway."""
    admin = await asyncpg.connect(config.dsn("postgres"))
    try:
        if not await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", config.TEST_DB_NAME):
            await admin.execute(f'CREATE DATABASE "{config.TEST_DB_NAME}"')
    finally:
        await admin.close()
    conn = await asyncpg.connect(config.dsn(config.TEST_DB_NAME))
    await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
    await init_conn(conn)
    await migrate(conn, config.MIGRATIONS_DIR)
    for table in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"):
        await conn.execute(f'ALTER TABLE "{table["tablename"]}" SET (autovacuum_enabled = false, vacuum_truncate = false)')
    yield conn
    await conn.close()


@pytest.fixture
async def conn(test_db):
    """Connection inside a transaction that is rolled back after each test."""
    tr = test_db.transaction()
    await tr.start()
    yield test_db
    await tr.rollback()


@pytest.fixture
async def client(conn):
    """HTTP client for the app; every request uses the test transaction's connection."""
    app.dependency_overrides[get_conn] = lambda: conn
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
