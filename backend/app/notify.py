"""One way to tell people something happened: a bell row per recipient (never the actor) + one push.send job."""
from collections.abc import Iterable

import asyncpg

from app.jobs import enqueue

# Negotiation timeline events → notification kinds.
IDEA_EVENT_KINDS = {
    "proposed": "proposal.created", "countered": "proposal.countered", "accepted": "proposal.accepted",
    "scheduled": "proposal.accepted", "refused": "proposal.refused", "cancelled": "proposal.cancelled",
    "done": "idea.done", "not_for_me": "idea.not_for_me", "reopened": "idea.reopened", "comment": "idea.comment",
}


async def notify(conn: asyncpg.Connection, actor_id: int | None, kind: str, payload: dict, recipients: Iterable[int]) -> list[int]:
    targets = sorted(set(recipients) - {actor_id})
    if not targets:
        return []
    actor_name = await conn.fetchval("SELECT display_name FROM users WHERE id = $1", actor_id) if actor_id else None
    full = {**payload, "actor_name": actor_name}
    ids = [r["id"] for r in await conn.fetch(
        "INSERT INTO notifications (user_id, kind, payload) SELECT u, $2, $3 FROM unnest($1::bigint[]) AS u RETURNING id", targets, kind, full)]
    await enqueue(conn, "push.send", {"notification_ids": ids})
    return ids


async def notify_space(conn: asyncpg.Connection, actor_id: int, space_id: int, kind: str, payload: dict) -> None:
    """Tell everyone else in the space."""
    members = [r["user_id"] for r in await conn.fetch("SELECT user_id FROM space_members WHERE space_id = $1", space_id)]
    await notify(conn, actor_id, kind, payload, members)


async def notify_idea(conn: asyncpg.Connection, actor_id: int, idea_id: int, event: str, extra: dict | None = None) -> None:
    """Tell the idea's other participants about a timeline event."""
    from app.routers.ideas import participants  # local import: routers import this module
    title = await conn.fetchval("SELECT title FROM ideas WHERE id = $1", idea_id)
    kind = IDEA_EVENT_KINDS.get(event, f"idea.{event}")
    await notify(conn, actor_id, kind, {"idea_id": idea_id, "title": title, **(extra or {})}, await participants(conn, idea_id))
