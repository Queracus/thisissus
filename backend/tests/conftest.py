import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from app import config
from app.db import get_conn
from app.main import app
from app.migrator import migrate


@pytest.fixture(scope="session")
async def test_db():
    """Fresh test database for the whole session, built by the real migrations."""
    admin = await asyncpg.connect(config.dsn("postgres"))
    await admin.execute(f'DROP DATABASE IF EXISTS "{config.TEST_DB_NAME}" WITH (FORCE)')
    await admin.execute(f'CREATE DATABASE "{config.TEST_DB_NAME}"')
    await admin.close()
    conn = await asyncpg.connect(config.dsn(config.TEST_DB_NAME))
    await migrate(conn, config.MIGRATIONS_DIR)
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
