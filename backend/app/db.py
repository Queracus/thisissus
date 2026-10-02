from fastapi import Request


async def get_conn(request: Request):
    """One pooled connection per request."""
    async with request.app.state.pool.acquire() as conn:
        yield conn
