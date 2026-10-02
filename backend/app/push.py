"""Web Push (worker job push.send): deliver bell notifications to subscribed phones/browsers, in each person's language.
Message texts mirror frontend/src/i18n/*.json → notifications.kind."""
import base64
import json
import logging

import asyncpg
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pywebpush import WebPushException, webpush
from starlette.concurrency import run_in_threadpool

from app import config

log = logging.getLogger("push")
TITLE = "Thisissus 💌"
TEXTS = {
    "sl": {"idea.created": "{actor} ima novo idejo: {title}", "proposal.created": "{actor} predlaga termin za {title}",
           "proposal.countered": "{actor} predlaga drug termin za {title}", "proposal.accepted": "{actor} je sprejel/a termin za {title} 💕",
           "proposal.refused": "{actor}: termin za {title} ne ustreza", "proposal.cancelled": "{actor} je preklical/a predlog za {title}",
           "idea.done": "{actor}: šla sta na {title}! Oceni ga 🎉", "idea.not_for_me": "{actor}: {title} ni zanj/zanjo",
           "idea.reopened": "{actor} je ponovno odprl/a {title}", "idea.comment": "{actor} je komentiral/a {title}",
           "date.tomorrow": "Jutri: {title} 💕", "rating.missing": "Kako je bilo na {title}? Oceni zmenek ❤️"},
    "en": {"idea.created": "{actor} has a new idea: {title}", "proposal.created": "{actor} proposes a time for {title}",
           "proposal.countered": "{actor} suggests another time for {title}", "proposal.accepted": "{actor} accepted the time for {title} 💕",
           "proposal.refused": "{actor}: the time for {title} doesn't work", "proposal.cancelled": "{actor} cancelled the proposal for {title}",
           "idea.done": "{actor}: you did {title}! Rate it 🎉", "idea.not_for_me": "{actor}: {title} isn't for them",
           "idea.reopened": "{actor} reopened {title}", "idea.comment": "{actor} commented on {title}",
           "date.tomorrow": "Tomorrow: {title} 💕", "rating.missing": "How was {title}? Rate the date ❤️"},
}
TEXT_FALLBACK = {"sl": "Nekaj novega v Thisissus", "en": "Something new in Thisissus"}


def b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def generate_vapid_keys() -> tuple[str, str]:
    """(public, private) base64url: the public key is what browsers pass as applicationServerKey."""
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    return b64encode(public), b64encode(key.private_numbers().private_value.to_bytes(32, "big"))


def message(locale: str, kind: str, payload: dict) -> dict:
    template = TEXTS.get(locale, TEXTS["sl"]).get(kind)
    body = template.format(actor=payload.get("actor_name") or "?", title=payload.get("title") or "") if template else TEXT_FALLBACK.get(locale, TEXT_FALLBACK["sl"])
    url = f"/ideas/{payload['idea_id']}" if "idea_id" in payload else f"/dates/{payload['date_id']}" if "date_id" in payload else "/"
    return {"title": TITLE, "body": body, "url": url}


def _deliver(sub: asyncpg.Record, data: str) -> int | None:
    """Blocking HTTP call (runs in a thread). Returns an HTTP status for failures, None on success."""
    try:
        webpush({"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}}, data,
                vapid_private_key=config.VAPID_PRIVATE_KEY, vapid_claims={"sub": config.VAPID_SUBJECT}, ttl=24 * 3600)
        return None
    except WebPushException as e:
        return getattr(e.response, "status_code", 0) or 0


async def send(conn: asyncpg.Connection, payload: dict) -> None:
    rows = await conn.fetch(
        """SELECT n.kind, n.payload, u.locale, s.id AS sub_id, s.endpoint, s.p256dh, s.auth
           FROM notifications n JOIN users u ON u.id = n.user_id JOIN push_subscriptions s ON s.user_id = n.user_id
           WHERE n.id = ANY($1::bigint[])""", payload["notification_ids"])
    for row in rows:
        data = json.dumps(message(row["locale"], row["kind"], row["payload"]), ensure_ascii=False)
        status = await run_in_threadpool(_deliver, row, data)
        if status in (404, 410):  # the browser dropped this subscription
            await conn.execute("DELETE FROM push_subscriptions WHERE id = $1", row["sub_id"])
        elif status is not None:
            log.warning("push to %s failed with %s", row["endpoint"][:40], status)
