import asyncpg
import pytest

from app.migrator import migrate


@pytest.fixture
async def scratch(conn, tmp_path):
    """Empty schema so migrator tests don't see the real migrations."""
    await conn.execute("CREATE SCHEMA mig_test; SET LOCAL search_path TO mig_test")
    return conn, tmp_path


async def test_applies_pending_files_in_order_and_records_them(scratch):
    conn, folder = scratch
    (folder / "002_add_col.sql").write_text("ALTER TABLE t ADD COLUMN b int;")
    (folder / "001_create.sql").write_text("CREATE TABLE t (a int);")

    applied = await migrate(conn, folder)

    assert applied == ["001_create", "002_add_col"]
    cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_schema='mig_test' AND table_name='t' ORDER BY ordinal_position")
    assert [c["column_name"] for c in cols] == ["a", "b"]
    assert [r["version"] for r in await conn.fetch("SELECT version FROM schema_migrations ORDER BY version")] == ["001_create", "002_add_col"]


async def test_second_run_only_applies_new_files(scratch):
    conn, folder = scratch
    (folder / "001_create.sql").write_text("CREATE TABLE t (a int);")
    await migrate(conn, folder)
    (folder / "002_add_col.sql").write_text("ALTER TABLE t ADD COLUMN b int;")

    assert await migrate(conn, folder) == ["002_add_col"]
    assert await migrate(conn, folder) == []


async def test_broken_file_rolls_back_entirely_and_raises(scratch):
    conn, folder = scratch
    (folder / "001_ok.sql").write_text("CREATE TABLE ok (a int);")
    (folder / "002_broken.sql").write_text("CREATE TABLE half (a int); SELECT * FROM missing_table;")

    with pytest.raises(asyncpg.UndefinedTableError):
        await migrate(conn, folder)

    tables = {r["table_name"] for r in await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='mig_test'")}
    assert tables == {"schema_migrations", "ok"}
    assert [r["version"] for r in await conn.fetch("SELECT version FROM schema_migrations")] == ["001_ok"]
