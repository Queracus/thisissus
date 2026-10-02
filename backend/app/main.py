from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import config
from app.db import init_conn
from app.errors import ApiError, api_error_handler, validation_error_handler
from app.migrator import migrate
from app.routers import admin, auth, dashboard, dates, health, ideas, links, me, media, notifications, photos, proposals, push, recipes, shares, shopping, spaces, tags, trash


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(config.dsn(), init=init_conn)
    async with app.state.pool.acquire() as conn:
        await migrate(conn, config.MIGRATIONS_DIR)
    yield
    await app.state.pool.close()


app = FastAPI(title="Thisissus", lifespan=lifespan)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


@app.middleware("http")
async def reject_foreign_origin(request: Request, call_next):
    """CSRF guard on top of SameSite=Lax: browsers always send Origin on mutating fetches."""
    origin = request.headers.get("origin")
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and origin and origin != config.ORIGIN:
        return JSONResponse({"code": "auth.bad_origin"}, status_code=403)
    return await call_next(request)


@app.middleware("http")
async def noindex_links(request: Request, call_next):
    """Secret-link pages must never end up in search engines."""
    response = await call_next(request)
    if request.url.path.startswith("/api/s/"):
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


# Every router must be listed here, otherwise it is never mounted.
for r in (health, auth, me, admin, spaces, dates, tags, photos, media, trash, ideas, proposals, notifications, push, recipes, shopping, shares, links, dashboard):
    app.include_router(r.router, prefix="/api")
app.include_router(recipes.photo_router, prefix="/api")
