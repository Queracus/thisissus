"""Postgres job queue. Producers call enqueue(); the worker process (app.worker) calls run_once() in a loop."""
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime

import asyncpg

Handler = Callable[[asyncpg.Connection, dict], Awaitable[None]]
MAX_ATTEMPTS = 5
LOCK_MINUTES = 10  # a crashed worker's job becomes claimable again after this
log = logging.getLogger("jobs")


async def enqueue(conn: asyncpg.Connection, kind: str, payload: dict, run_at: datetime | None = None, dedupe_key: str | None = None) -> int | None:
    """Queue a job; returns its id, or None when dedupe_key already exists."""
    return await conn.fetchval(
        "INSERT INTO jobs (kind, payload, run_at, dedupe_key) VALUES ($1, $2, coalesce($3, now()), $4) ON CONFLICT (dedupe_key) DO NOTHING RETURNING id",
        kind, payload, run_at, dedupe_key)


async def claim(conn: asyncpg.Connection, kind: str | None = None) -> asyncpg.Record | None:
    """Atomically take one due job; concurrent workers skip rows another worker has locked."""
    return await conn.fetchrow(
        f"""UPDATE jobs SET locked_until = now() + interval '{LOCK_MINUTES} minutes', attempts = attempts + 1
            WHERE id = (SELECT id FROM jobs
                        WHERE done_at IS NULL AND failed_at IS NULL AND run_at <= now()
                          AND (locked_until IS NULL OR locked_until < now()) AND ($1::text IS NULL OR kind = $1)
                        ORDER BY run_at, id LIMIT 1 FOR UPDATE SKIP LOCKED)
            RETURNING *""", kind)


async def _finish(conn: asyncpg.Connection, job: asyncpg.Record, error: str | None) -> None:
    if error is None:
        await conn.execute("UPDATE jobs SET done_at = now(), locked_until = NULL WHERE id = $1", job["id"])
    elif job["attempts"] >= MAX_ATTEMPTS:
        await conn.execute("UPDATE jobs SET failed_at = now(), locked_until = NULL, last_error = $2 WHERE id = $1", job["id"], error)
    else:  # exponential backoff: 2, 4, 8, 16 minutes
        await conn.execute(
            "UPDATE jobs SET run_at = now() + make_interval(mins => power(2, attempts)::int), locked_until = NULL, last_error = $2 WHERE id = $1",
            job["id"], error)


async def run_once(conn: asyncpg.Connection, handlers: dict[str, Handler]) -> bool:
    """Claim and run one job. Returns False when nothing was due."""
    job = await claim(conn)
    if not job:
        return False
    error = None
    try:
        handler = handlers.get(job["kind"])
        if handler is None:
            raise LookupError(f"no handler for {job['kind']}")
        async with conn.transaction():  # a failing handler's writes are rolled back
            await handler(conn, job["payload"])
    except Exception as e:  # noqa: BLE001 - any handler error is recorded on the job
        error = f"{type(e).__name__}: {e}"
        log.warning("job %s (%s) failed: %s", job["id"], job["kind"], error)
    await _finish(conn, job, error)
    return True


async def schedule_periodic(conn: asyncpg.Connection, intervals: dict[str, int]) -> None:
    """Enqueue each periodic kind at most once per interval (seconds), safe to call repeatedly."""
    for kind, seconds in intervals.items():
        bucket = await conn.fetchval("SELECT floor(extract(epoch FROM now()) / $1)::bigint", seconds)
        await enqueue(conn, kind, {}, dedupe_key=f"{kind}:{bucket}")
