"""WebAuthn (passkeys) on top of py_webauthn. Challenges live in auth_challenges and are consumed once."""
import json
from datetime import timedelta

import asyncpg
from webauthn import (generate_authentication_options, generate_registration_options, options_to_json,
                      verify_authentication_response, verify_registration_response)
from webauthn.helpers import base64url_to_bytes, parse_client_data_json
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor, ResidentKeyRequirement,
                                      UserVerificationRequirement)

from app import config
from app.errors import ApiError

CHALLENGE_TTL = timedelta(minutes=5)


async def _store_challenge(conn: asyncpg.Connection, challenge: bytes, purpose: str, user_id: int | None = None) -> None:
    await conn.execute("INSERT INTO auth_challenges (challenge, purpose, user_id, expires_at) VALUES ($1, $2, $3, now() + $4)", challenge, purpose, user_id, CHALLENGE_TTL)


async def _take_challenge(conn: asyncpg.Connection, credential: dict, purpose: str, user_id: int | None = None) -> bytes:
    try:
        challenge = parse_client_data_json(base64url_to_bytes(credential["response"]["clientDataJSON"])).challenge
    except (KeyError, TypeError, ValueError, WebAuthnException):
        raise ApiError(400, "auth.passkey_invalid")
    row = await conn.fetchrow(
        "DELETE FROM auth_challenges WHERE challenge = $1 AND purpose = $2 AND user_id IS NOT DISTINCT FROM $3::bigint AND expires_at > now() RETURNING challenge",
        challenge, purpose, user_id)
    if not row:
        raise ApiError(400, "auth.challenge_invalid")
    return row["challenge"]


async def registration_options(conn: asyncpg.Connection, user: asyncpg.Record) -> dict:
    existing = await conn.fetch("SELECT credential_id FROM passkeys WHERE user_id = $1", user["id"])
    opts = generate_registration_options(
        rp_id=config.RP_ID, rp_name=config.RP_NAME, user_id=str(user["id"]).encode(), user_name=user["display_name"],
        authenticator_selection=AuthenticatorSelectionCriteria(resident_key=ResidentKeyRequirement.REQUIRED,
                                                               user_verification=UserVerificationRequirement.PREFERRED),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=r["credential_id"]) for r in existing])
    await _store_challenge(conn, opts.challenge, "register", user["id"])
    return json.loads(options_to_json(opts))


async def register_passkey(conn: asyncpg.Connection, user_id: int, credential: dict) -> None:
    challenge = await _take_challenge(conn, credential, "register", user_id)
    try:
        v = verify_registration_response(credential=credential, expected_challenge=challenge,
                                         expected_rp_id=config.RP_ID, expected_origin=config.ORIGIN)
    except (WebAuthnException, KeyError, TypeError, ValueError):
        raise ApiError(400, "auth.passkey_invalid")
    await conn.execute(
        "INSERT INTO passkeys (user_id, credential_id, public_key, sign_count, transports) VALUES ($1, $2, $3, $4, $5)",
        user_id, v.credential_id, v.credential_public_key, v.sign_count, credential["response"].get("transports") or [])


async def authentication_options(conn: asyncpg.Connection) -> dict:
    opts = generate_authentication_options(rp_id=config.RP_ID)  # discoverable credentials: no allow list
    await _store_challenge(conn, opts.challenge, "login")
    return json.loads(options_to_json(opts))


async def authenticate(conn: asyncpg.Connection, credential: dict) -> int:
    """Verify an assertion and return the user id."""
    challenge = await _take_challenge(conn, credential, "login")
    try:
        pk = await conn.fetchrow("SELECT * FROM passkeys WHERE credential_id = $1", base64url_to_bytes(credential["rawId"]))
        if not pk:
            raise ApiError(400, "auth.passkey_unknown")
        v = verify_authentication_response(credential=credential, expected_challenge=challenge, expected_rp_id=config.RP_ID,
                                           expected_origin=config.ORIGIN, credential_public_key=pk["public_key"],
                                           credential_current_sign_count=pk["sign_count"])
    except (WebAuthnException, KeyError, TypeError, ValueError):
        raise ApiError(400, "auth.passkey_invalid")
    await conn.execute("UPDATE passkeys SET sign_count = $2 WHERE id = $1", pk["id"], v.new_sign_count)
    return pk["user_id"]
