from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from app import config
from app.migrator import migrate
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(config.dsn())
    async with app.state.pool.acquire() as conn:
        await migrate(conn, config.MIGRATIONS_DIR)
    yield
    await app.state.pool.close()


app = FastAPI(title="Thisissus", lifespan=lifespan)

# Every router must be listed here, otherwise it is never mounted.
for r in (health,):
    app.include_router(r.router, prefix="/api")
