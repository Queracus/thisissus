import asyncio

import asyncpg

from app import config
from app.db import init_conn
from app.jobs import MAX_ATTEMPTS, claim, enqueue, run_once, schedule_periodic
from tests.helpers import signup


async def test_enqueued_job_is_claimed_and_completed_once(conn):
    calls = []

    async def handler(c, payload):
        calls.append(payload)

    await enqueue(conn, "test.echo", {"n": 1})

    assert await run_once(conn, {"test.echo": handler}) is True
    assert calls == [{"n": 1}]
    assert await run_once(conn, {"test.echo": handler}) is False


async def test_failure_is_recorded_and_retried_later(conn):
    async def boom(c, payload):
        raise RuntimeError("disk full")

    job_id = await enqueue(conn, "test.boom", {})
    await run_once(conn, {"test.boom": boom})

    job = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
    assert (job["attempts"], job["last_error"], job["done_at"]) == (1, "RuntimeError: disk full", None)
    assert job["run_at"] > await conn.fetchval("SELECT now()")
    assert await claim(conn) is None  # backoff: not yet due


async def test_job_gives_up_after_max_attempts(conn):
    async def boom(c, payload):
        raise RuntimeError("nope")

    job_id = await enqueue(conn, "test.boom", {})
    for _ in range(MAX_ATTEMPTS):
        await conn.execute("UPDATE jobs SET run_at = now() WHERE id = $1", job_id)  # time travel past backoff
        await run_once(conn, {"test.boom": boom})

    job = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
    assert job["attempts"] == MAX_ATTEMPTS and job["failed_at"] is not None
    await conn.execute("UPDATE jobs SET run_at = now() WHERE id = $1", job_id)
    assert await claim(conn) is None


async def test_unknown_kind_fails_instead_of_looping(conn):
    job_id = await enqueue(conn, "test.unknown", {})

    await run_once(conn, {})

    assert "no handler" in await conn.fetchval("SELECT last_error FROM jobs WHERE id = $1", job_id)


async def test_periodic_job_is_scheduled_once_per_period(conn):
    await schedule_periodic(conn, {"test.tick": 3600})
    await schedule_periodic(conn, {"test.tick": 3600})

    assert await conn.fetchval("SELECT count(*) FROM jobs WHERE kind = 'test.tick'") == 1


async def test_two_workers_never_claim_the_same_job(test_db):
    """Real concurrency: two separate connections outside the test transaction."""
    a = await asyncpg.connect(config.dsn(config.TEST_DB_NAME))
    b = await asyncpg.connect(config.dsn(config.TEST_DB_NAME))
    await init_conn(a)
    await init_conn(b)
    try:
        await a.execute("DELETE FROM jobs WHERE kind = 'test.race'")
        for i in range(10):
            await enqueue(a, "test.race", {"i": i})

        async def drain(c):
            got = []
            while job := await claim(c, kind="test.race"):
                got.append(job["id"])
            return got

        got_a, got_b = await asyncio.gather(drain(a), drain(b))

        assert len(got_a) + len(got_b) == 10
        assert not set(got_a) & set(got_b)
    finally:
        await a.execute("DELETE FROM jobs WHERE kind = 'test.race'")
        await a.close()
        await b.close()


async def test_admin_sees_failed_jobs(client, conn):
    await signup(client, conn, "Ana", roles=["admin"])
    job_id = await enqueue(conn, "test.boom", {})
    await conn.execute("UPDATE jobs SET failed_at = now(), attempts = 5, last_error = 'x' WHERE id = $1", job_id)

    jobs = (await client.get("/api/admin/jobs?failed=1")).json()

    assert [(j["id"], j["kind"], j["last_error"]) for j in jobs] == [(job_id, "test.boom", "x")]
