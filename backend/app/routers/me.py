import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.deps import current_user
from app.auth.pin import set_pin
from app.db import get_conn

router = APIRouter(prefix="/me")


class PinIn(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9._-]{3,30}$")
    pin: str = Field(pattern=r"^\d{6}$")


@router.put("/pin")
async def put_pin(body: PinIn, user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await set_pin(conn, user["id"], body.username, body.pin)
    return {"ok": True}
