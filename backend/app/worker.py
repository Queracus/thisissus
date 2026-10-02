"""Background worker: python -m app.worker

Runs jobs from the queue (media processing, push, reminders, trash purge). CPU-heavy work lives here, never in the API.
Register handlers with @handler("kind"); periodic kinds go in PERIODIC (seconds).
"""
import asyncio
import logging

import asyncpg

from app import config
from app.db import init_conn
from app.jobs import Handler, run_once, schedule_periodic
from app.media.derive import derive_media
from app.export import export_all
from app.migrator import migrate
from app.push import send as push_send
from app.reminders import tick as reminders_tick
from app.trash import purge_expired

# Every job kind must be listed here, otherwise it fails with 'no handler'.
HANDLERS: dict[str, Handler] = {
    "media.derive": derive_media,
    "trash.purge": purge_expired,
    "push.send": push_send,
    "reminders.tick": reminders_tick,
    "media.export": export_all,
}
PERIODIC: dict[str, int] = {
    "trash.purge": 24 * 3600,
    "reminders.tick": 3600,
}
IDLE_SECONDS = 2


def handler(kind: str):
    def register(fn: Handler) -> Handler:
        HANDLERS[kind] = fn
        return fn
    return register


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    conn = await asyncpg.connect(config.dsn())
    await init_conn(conn)
    await migrate(conn, config.MIGRATIONS_DIR)
    logging.getLogger("worker").info("started with handlers %s", sorted(HANDLERS))
    while True:
        await schedule_periodic(conn, PERIODIC)
        while await run_once(conn, HANDLERS):
            pass
        await asyncio.sleep(IDLE_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
