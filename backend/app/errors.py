from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Error with a stable code the frontend translates, e.g. ApiError(400, "auth.invalid_token").
    Extra keyword fields (e.g. retry_after=900) are added to the JSON body."""

    def __init__(self, status: int, code: str, **extra):
        self.status, self.code, self.extra = status, code, extra


async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse({"code": exc.code, **exc.extra}, status_code=exc.status)


async def validation_error_handler(request: Request, exc: RequestValidationError):
    fields = [".".join(str(p) for p in e["loc"][1:]) for e in exc.errors()]
    return JSONResponse({"code": "validation.invalid", "fields": fields}, status_code=422)
