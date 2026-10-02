"""Time negotiation for date ideas, as a pure state machine (no I/O; the router loads, applies and saves).

    idea --propose--> pending --accept (everyone)--> scheduled
                        |  ^ counter (any participant; also from scheduled = reschedule)
                        |--refuse / cancel--> idea
    idea|pending|scheduled --not for me--> archived --reopen--> idea

The first accept narrows a multi-slot proposal to that slot; other participants then accept it or counter.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime

MAX_SLOTS = 3


class TransitionError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Proposal:
    id: int | None              # None = new, not saved yet
    proposed_by: int
    slots: tuple[datetime, ...]
    accepted: frozenset[int] = frozenset()
    status: str = "open"        # open | accepted


@dataclass(frozen=True)
class IdeaState:
    status: str                 # idea | pending | scheduled | archived
    participants: frozenset[int]
    proposal: Proposal | None = None
    scheduled_at: datetime | None = None


@dataclass(frozen=True)
class Propose:
    actor: int
    slots: tuple[datetime, ...]


@dataclass(frozen=True)
class Counter:
    actor: int
    slots: tuple[datetime, ...]


@dataclass(frozen=True)
class Accept:
    actor: int
    slot: datetime


@dataclass(frozen=True)
class Refuse:
    actor: int


@dataclass(frozen=True)
class Cancel:
    actor: int


@dataclass(frozen=True)
class NotForMe:
    actor: int


@dataclass(frozen=True)
class Reopen:
    actor: int


@dataclass(frozen=True)
class Result:
    state: IdeaState
    event: str                                       # timeline kind: proposed | countered | accepted | scheduled | refused | cancelled
    closed: tuple[tuple[int, str], ...] = field(default=())  # (saved proposal id, final status)


def _slots(slots: tuple[datetime, ...], now: datetime) -> tuple[datetime, ...]:
    unique = tuple(sorted(set(slots)))
    if not 1 <= len(unique) <= MAX_SLOTS:
        raise TransitionError("proposal.slot_count")
    if unique[0] <= now:
        raise TransitionError("proposal.slot_in_past")
    return unique


def _require(cond: bool, code: str) -> None:
    if not cond:
        raise TransitionError(code)


def _closing(proposal: Proposal | None, status: str) -> tuple[tuple[int, str], ...]:
    return ((proposal.id, status),) if proposal and proposal.id is not None else ()


def transition(state: IdeaState, event, now: datetime) -> Result:
    _require(event.actor in state.participants, "proposal.not_participant")
    p = state.proposal

    if isinstance(event, Propose):
        _require(state.status == "idea", "proposal.invalid_state")
        new = Proposal(id=None, proposed_by=event.actor, slots=_slots(event.slots, now))
        return Result(replace(state, status="pending", proposal=new, scheduled_at=None), "proposed")

    if isinstance(event, Counter):
        _require(state.status in ("pending", "scheduled"), "proposal.invalid_state")
        new = Proposal(id=None, proposed_by=event.actor, slots=_slots(event.slots, now))
        return Result(replace(state, status="pending", proposal=new, scheduled_at=None), "countered", _closing(p, "superseded"))

    if isinstance(event, NotForMe):  # pass on the idea itself (archived, not deleted)
        _require(state.status in ("idea", "pending", "scheduled"), "proposal.invalid_state")
        return Result(replace(state, status="archived", proposal=None, scheduled_at=None), "not_for_me", _closing(p, "cancelled"))

    if isinstance(event, Reopen):
        _require(state.status == "archived", "proposal.invalid_state")
        return Result(replace(state, status="idea"), "reopened")

    _require(state.status == "pending" and p is not None, "proposal.invalid_state")

    if isinstance(event, Accept):
        _require(event.actor != p.proposed_by, "proposal.own_proposal")
        _require(event.actor not in p.accepted, "proposal.already_answered")
        _require(event.slot in p.slots, "proposal.unknown_slot")
        accepted = p.accepted | {event.actor}
        narrowed = replace(p, slots=(event.slot,), accepted=accepted)
        if accepted >= state.participants - {p.proposed_by}:
            return Result(replace(state, status="scheduled", scheduled_at=event.slot, proposal=replace(narrowed, status="accepted")), "scheduled")
        return Result(replace(state, proposal=narrowed), "accepted")

    if isinstance(event, Refuse):
        _require(event.actor != p.proposed_by, "proposal.own_proposal")
        return Result(replace(state, status="idea", proposal=None, scheduled_at=None), "refused", _closing(p, "refused"))

    if isinstance(event, Cancel):
        _require(event.actor == p.proposed_by, "proposal.not_proposer")
        return Result(replace(state, status="idea", proposal=None, scheduled_at=None), "cancelled", _closing(p, "cancelled"))

    raise TransitionError("proposal.unknown_event")
