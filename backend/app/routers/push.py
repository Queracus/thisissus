import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app import config
from app.auth.deps import current_user
from app.db import get_conn

router = APIRouter(prefix="/push")


class Keys(BaseModel):
    p256dh: str = Field(max_length=200)
    auth: str = Field(max_length=100)


class SubscriptionIn(BaseModel):
    endpoint: str = Field(pattern=r"^https://", max_length=1000)
    keys: Keys


class EndpointIn(BaseModel):
    endpoint: str


@router.get("/public-key")
async def public_key(_=Depends(current_user)):
    return {"key": config.VAPID_PUBLIC_KEY}


@router.post("/subscriptions")
async def subscribe(body: SubscriptionIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    """Upsert by endpoint: a device that changes owner (logout/login) follows the new user."""
    await conn.execute(
        """INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth) VALUES ($1, $2, $3, $4)
           ON CONFLICT (endpoint) DO UPDATE SET user_id = $1, p256dh = $3, auth = $4""",
        user["id"], body.endpoint, body.keys.p256dh, body.keys.auth)
    return {"ok": True}


@router.delete("/subscriptions")
async def unsubscribe(body: EndpointIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await conn.execute("DELETE FROM push_subscriptions WHERE endpoint = $1 AND user_id = $2", body.endpoint, user["id"])
    return {"ok": True}
