"""HTTP + persistence around the pure state machine in app.proposals: load → transition → save, under a row lock."""
from datetime import UTC, datetime

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import AwareDatetime, BaseModel, Field

from app.auth.deps import current_user
from app.db import get_conn
from app.errors import ApiError
from app.proposals import Accept, Cancel, Counter, DidIt, IdeaState, NotForMe, Propose, Proposal, Refuse, Reopen, Result, TransitionError, transition
from app.routers.ideas import participants, visible_idea

router = APIRouter(prefix="/ideas")


class SlotsIn(BaseModel):
    slots: list[AwareDatetime] = Field(max_length=10)


class SlotIn(BaseModel):
    slot: AwareDatetime


class CommentIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


async def live_proposal(conn: asyncpg.Connection, idea_id: int) -> Proposal | None:
    row = await conn.fetchrow("SELECT * FROM proposals WHERE idea_id = $1 AND status IN ('open', 'accepted')", idea_id)
    if not row:
        return None
    slots = tuple(r["starts_at"] for r in await conn.fetch("SELECT starts_at FROM proposal_slots WHERE proposal_id = $1 ORDER BY starts_at", row["id"]))
    accepted = frozenset(r["user_id"] for r in await conn.fetch("SELECT user_id FROM proposal_responses WHERE proposal_id = $1", row["id"]))
    return Proposal(id=row["id"], proposed_by=row["proposed_by"], slots=slots, accepted=accepted, status=row["status"])


async def load_state(conn: asyncpg.Connection, idea_id: int) -> IdeaState:
    idea = await conn.fetchrow("SELECT status, scheduled_at FROM ideas WHERE id = $1 FOR UPDATE", idea_id)  # serialize concurrent answers
    return IdeaState(status=idea["status"], participants=await participants(conn, idea_id),
                     proposal=await live_proposal(conn, idea_id), scheduled_at=idea["scheduled_at"])


async def save(conn: asyncpg.Connection, idea_id: int, actor: int, result: Result, payload: dict) -> None:
    for proposal_id, status in result.closed:
        await conn.execute("UPDATE proposals SET status = $2 WHERE id = $1", proposal_id, status)
    p = result.state.proposal
    if p and p.id is None:
        pid = await conn.fetchval("INSERT INTO proposals (idea_id, proposed_by, status) VALUES ($1, $2, $3) RETURNING id", idea_id, p.proposed_by, p.status)
        await conn.executemany("INSERT INTO proposal_slots (proposal_id, starts_at) VALUES ($1, $2)", [(pid, s) for s in p.slots])
    elif p:
        await conn.execute("UPDATE proposals SET status = $2 WHERE id = $1", p.id, p.status)
        await conn.execute("DELETE FROM proposal_slots WHERE proposal_id = $1 AND NOT starts_at = ANY($2::timestamptz[])", p.id, list(p.slots))
        await conn.executemany("INSERT INTO proposal_responses (proposal_id, user_id, starts_at) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                               [(p.id, u, p.slots[0]) for u in p.accepted])
    await conn.execute("UPDATE ideas SET status = $2, scheduled_at = $3, updated_at = now() WHERE id = $1",
                       idea_id, result.state.status, result.state.scheduled_at)
    await add_event(conn, idea_id, actor, result.event, payload)


async def add_event(conn: asyncpg.Connection, idea_id: int, actor: int, kind: str, payload: dict) -> None:
    await conn.execute("INSERT INTO idea_events (idea_id, actor_id, kind, payload) VALUES ($1, $2, $3, $4)", idea_id, actor, kind, payload)


async def run(conn: asyncpg.Connection, user: asyncpg.Record, idea_id: int, make_event, payload: dict, after=None) -> dict:
    """Load → transition → save under a row lock. `after(state_before)` may add side effects in the same transaction."""
    await visible_idea(conn, user["id"], idea_id)
    async with conn.transaction():
        state = await load_state(conn, idea_id)
        try:
            result = transition(state, make_event(user["id"]), datetime.now(UTC))
        except TransitionError as e:
            raise ApiError(409, e.code)
        if after:
            payload = {**payload, **await after(state)}
        await save(conn, idea_id, user["id"], result, payload)
    return await visible_idea(conn, user["id"], idea_id)


class DidItIn(BaseModel):
    archive: bool = False


async def create_date_from_idea(conn: asyncpg.Connection, idea_id: int, user_id: int, when: datetime) -> int:
    """Pre-filled Date We've Had: title, estimated cost and tags from the idea; time = agreed slot or now."""
    date_id = await conn.fetchval(
        """INSERT INTO dates (space_id, title, starts_at, cost, created_by, idea_id)
           SELECT space_id, title, $3, est_cost, $2, id FROM ideas WHERE id = $1 RETURNING id""", idea_id, user_id, when)
    await conn.execute("INSERT INTO date_tags (date_id, tag_id) SELECT $1, tag_id FROM idea_tags WHERE idea_id = $2", date_id, idea_id)
    await conn.execute("UPDATE ideas SET times_done = times_done + 1 WHERE id = $1", idea_id)
    return date_id


def iso_z(dt: datetime) -> str:
    """UTC ISO with Z, the same format the pydantic response models use."""
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _iso(slots) -> list[str]:
    return [iso_z(s) for s in slots]


@router.post("/{idea_id}/propose")
async def propose(idea_id: int, body: SlotsIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await run(conn, user, idea_id, lambda u: Propose(u, tuple(body.slots)), {"slots": _iso(body.slots)})


@router.post("/{idea_id}/counter")
async def counter(idea_id: int, body: SlotsIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await run(conn, user, idea_id, lambda u: Counter(u, tuple(body.slots)), {"slots": _iso(body.slots)})


@router.post("/{idea_id}/accept")
async def accept(idea_id: int, body: SlotIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await run(conn, user, idea_id, lambda u: Accept(u, body.slot), {"slot": iso_z(body.slot)})


@router.post("/{idea_id}/refuse")
async def refuse(idea_id: int, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await run(conn, user, idea_id, Refuse, {})


@router.post("/{idea_id}/cancel")
async def cancel(idea_id: int, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await run(conn, user, idea_id, Cancel, {})


@router.post("/{idea_id}/not-for-me")
async def not_for_me(idea_id: int, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await run(conn, user, idea_id, NotForMe, {})


@router.post("/{idea_id}/reopen")
async def reopen(idea_id: int, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    return await run(conn, user, idea_id, Reopen, {})


@router.post("/{idea_id}/did-it")
async def did_it(idea_id: int, body: DidItIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    created = {}

    async def make_date(before: IdeaState) -> dict:
        created["date_id"] = await create_date_from_idea(conn, idea_id, user["id"], before.scheduled_at or datetime.now(UTC))
        return created

    idea = await run(conn, user, idea_id, lambda u: DidIt(u, body.archive), {}, after=make_date)
    return {"idea": idea, "date_id": created["date_id"]}


@router.post("/{idea_id}/comments")
async def comment(idea_id: int, body: CommentIn, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await visible_idea(conn, user["id"], idea_id)
    await add_event(conn, idea_id, user["id"], "comment", {"text": body.text})
    return {"ok": True}


@router.get("/{idea_id}/timeline")
async def timeline(idea_id: int, user=Depends(current_user), conn: asyncpg.Connection = Depends(get_conn)):
    await visible_idea(conn, user["id"], idea_id)
    p = await live_proposal(conn, idea_id)
    proposal = None
    if p:
        everyone = await participants(conn, idea_id)
        proposal = {"id": p.id, "proposed_by": p.proposed_by, "status": p.status, "slots": _iso(p.slots),
                    "proposed_by_name": await conn.fetchval("SELECT display_name FROM users WHERE id = $1", p.proposed_by),
                    "accepted": sorted(p.accepted),
                    "pending": sorted(everyone - {p.proposed_by} - p.accepted) if p.status == "open" else [],
                    "pending_names": [r["display_name"] for r in await conn.fetch(
                        "SELECT display_name FROM users WHERE id = ANY($1::bigint[]) ORDER BY display_name",
                        sorted(everyone - {p.proposed_by} - p.accepted) if p.status == "open" else [])],
                    "awaiting_me": p.status == "open" and user["id"] != p.proposed_by and user["id"] not in p.accepted}
    events = await conn.fetch(
        """SELECT e.id, e.kind, e.payload, e.created_at, e.actor_id, u.display_name AS actor_name
           FROM idea_events e LEFT JOIN users u ON u.id = e.actor_id WHERE e.idea_id = $1 ORDER BY e.id""", idea_id)
    return {"proposal": proposal, "events": [dict(e) for e in events]}
