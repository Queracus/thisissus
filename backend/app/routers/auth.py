import asyncpg
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.auth.deps import current_user
from app.auth.pin import check_pin
from app.auth.roles import user_permissions
from app.auth.passkeys import authenticate, authentication_options, register_passkey, registration_options
from app.auth.sessions import COOKIE, create_session, delete_session, set_session_cookie
from app.auth.tokens import use_token, valid_token
from app.db import get_conn

router = APIRouter(prefix="/auth")
PASSKEY_TOKENS = ("invite", "recovery")  # both let a user register a new passkey


class TokenIn(BaseModel):
    token: str


class RegisterIn(BaseModel):
    token: str
    credential: dict


class LoginIn(BaseModel):
    credential: dict


class PinLoginIn(BaseModel):
    username: str
    pin: str


async def me_out(conn: asyncpg.Connection, user: asyncpg.Record) -> dict:
    return {"id": user["id"], "display_name": user["display_name"], "username": user["username"], "locale": user["locale"],
            "permissions": await user_permissions(conn, user["id"])}


async def _login(conn: asyncpg.Connection, request: Request, response: Response, user_id: int) -> dict:
    set_session_cookie(response, await create_session(conn, user_id, request.headers.get("user-agent")))
    return await me_out(conn, await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id))


@router.post("/passkey/register/options")
async def register_options(body: TokenIn, conn: asyncpg.Connection = Depends(get_conn)):
    tok = await valid_token(conn, body.token, PASSKEY_TOKENS)
    return await registration_options(conn, await conn.fetchrow("SELECT * FROM users WHERE id = $1", tok["user_id"]))


@router.post("/passkey/register/verify")
async def register_verify(body: RegisterIn, request: Request, response: Response, conn: asyncpg.Connection = Depends(get_conn)):
    tok = await valid_token(conn, body.token, PASSKEY_TOKENS)
    async with conn.transaction():
        await register_passkey(conn, tok["user_id"], body.credential)
        await use_token(conn, body.token)
        if tok["space_id"]:
            await conn.execute("INSERT INTO space_members (space_id, user_id, role) VALUES ($1, $2, 'member') ON CONFLICT DO NOTHING",
                               tok["space_id"], tok["user_id"])
        return await _login(conn, request, response, tok["user_id"])


@router.post("/passkey/login/options")
async def login_options(conn: asyncpg.Connection = Depends(get_conn)):
    return await authentication_options(conn)


@router.post("/passkey/login/verify")
async def login_verify(body: LoginIn, request: Request, response: Response, conn: asyncpg.Connection = Depends(get_conn)):
    async with conn.transaction():
        return await _login(conn, request, response, await authenticate(conn, body.credential))


@router.post("/pin/login")
async def pin_login(body: PinLoginIn, request: Request, response: Response, conn: asyncpg.Connection = Depends(get_conn)):
    user_id = await check_pin(conn, body.username, body.pin, request.client.host)
    return await _login(conn, request, response, user_id)


@router.post("/logout")
async def logout(request: Request, response: Response, conn: asyncpg.Connection = Depends(get_conn)):
    if raw := request.cookies.get(COOKIE):
        await delete_session(conn, raw)
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: asyncpg.Record = Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await me_out(conn, user)
