from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Error with a stable code the frontend translates, e.g. ApiError(400, "auth.invalid_token")."""

    def __init__(self, status: int, code: str):
        self.status, self.code = status, code


async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse({"code": exc.code}, status_code=exc.status)
