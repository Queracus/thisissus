"""Pure state-machine tests: no database, every rule of the negotiation."""
from datetime import UTC, datetime, timedelta

import pytest

from app.proposals import Accept, Cancel, Counter, IdeaState, NotForMe, Propose, Proposal, Refuse, Reopen, TransitionError, transition

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
FRI, SAT, SUN = (NOW + timedelta(days=d) for d in (3, 4, 5))
ANA, BOR, EVE = 1, 2, 3
COUPLE = frozenset({ANA, BOR})


def idea(**kw) -> IdeaState:
    return IdeaState(status="idea", participants=COUPLE, **kw)


def pending(proposer=ANA, slots=(FRI, SAT), accepted=frozenset(), participants=COUPLE, pid=7) -> IdeaState:
    return IdeaState(status="pending", participants=participants,
                     proposal=Proposal(id=pid, proposed_by=proposer, slots=slots, accepted=accepted))


def err(state, event) -> str:
    with pytest.raises(TransitionError) as e:
        transition(state, event, NOW)
    return e.value.code


def test_propose_one_to_three_times_makes_it_pending():
    r = transition(idea(), Propose(ANA, (FRI, SAT, SUN)), NOW)

    assert r.state.status == "pending"
    assert (r.state.proposal.id, r.state.proposal.proposed_by, r.state.proposal.slots) == (None, ANA, (FRI, SAT, SUN))
    assert r.event == "proposed"


def test_propose_rejects_bad_slot_counts_past_times_and_outsiders():
    assert err(idea(), Propose(ANA, ())) == "proposal.slot_count"
    assert err(idea(), Propose(ANA, (FRI, SAT, SUN, SUN + timedelta(hours=1)))) == "proposal.slot_count"
    assert err(idea(), Propose(ANA, (NOW - timedelta(hours=1),))) == "proposal.slot_in_past"
    assert err(idea(), Propose(EVE, (FRI,))) == "proposal.not_participant"


def test_duplicate_slots_collapse_and_are_sorted():
    assert transition(idea(), Propose(ANA, (SAT, FRI, SAT)), NOW).state.proposal.slots == (FRI, SAT)


def test_partner_accepting_schedules_it_in_a_couple():
    r = transition(pending(), Accept(BOR, SAT), NOW)

    assert (r.state.status, r.state.scheduled_at) == ("scheduled", SAT)
    assert (r.state.proposal.slots, r.state.proposal.status) == ((SAT,), "accepted")
    assert r.event == "scheduled"


def test_proposer_cannot_accept_own_proposal_and_slot_must_be_offered():
    assert err(pending(), Accept(ANA, FRI)) == "proposal.own_proposal"
    assert err(pending(), Accept(BOR, SUN)) == "proposal.unknown_slot"


def test_refusing_the_time_returns_to_a_plain_idea():
    r = transition(pending(), Refuse(BOR), NOW)

    assert (r.state.status, r.state.proposal, r.state.scheduled_at) == ("idea", None, None)
    assert r.closed == ((7, "refused"),)
    assert err(pending(), Refuse(ANA)) == "proposal.own_proposal"


def test_counter_supersedes_and_flips_who_must_answer():
    r = transition(pending(), Counter(BOR, (SUN,)), NOW)

    assert r.state.status == "pending"
    assert (r.state.proposal.id, r.state.proposal.proposed_by, r.state.proposal.slots) == (None, BOR, (SUN,))
    assert r.closed == ((7, "superseded"),)
    assert transition(r.state, Accept(ANA, SUN), NOW).state.status == "scheduled"


def test_ping_pong_until_agreed():
    state = idea()
    for event in (Propose(ANA, (FRI,)), Counter(BOR, (SAT, SUN)), Counter(ANA, (SUN,)), Accept(BOR, SUN)):
        state = transition(state, event, NOW).state
    assert (state.status, state.scheduled_at) == ("scheduled", SUN)


def test_scheduled_date_can_be_rescheduled_by_counter():
    scheduled = transition(pending(), Accept(BOR, FRI), NOW).state

    r = transition(scheduled, Counter(BOR, (SUN,)), NOW)

    assert (r.state.status, r.state.scheduled_at, r.state.proposal.proposed_by) == ("pending", None, BOR)
    assert r.closed == ((7, "superseded"),)


def test_only_proposer_cancels():
    assert transition(pending(), Cancel(ANA), NOW).state.status == "idea"
    assert err(pending(), Cancel(BOR)) == "proposal.not_proposer"


def test_events_in_the_wrong_state_are_rejected():
    assert err(idea(), Accept(BOR, FRI)) == "proposal.invalid_state"
    assert err(idea(), Refuse(BOR)) == "proposal.invalid_state"
    assert err(idea(), Counter(BOR, (FRI,))) == "proposal.invalid_state"
    assert err(pending(), Propose(ANA, (FRI,))) == "proposal.invalid_state"
    archived = IdeaState(status="archived", participants=COUPLE)
    assert err(archived, Propose(ANA, (FRI,))) == "proposal.invalid_state"


def test_group_needs_everyone_and_first_accept_narrows_the_slot():
    trio = frozenset({ANA, BOR, EVE})
    first = transition(pending(participants=trio), Accept(BOR, SAT), NOW)

    assert (first.state.status, first.state.proposal.slots, first.state.proposal.accepted) == ("pending", (SAT,), frozenset({BOR}))
    assert first.event == "accepted"
    assert err(first.state, Accept(EVE, FRI)) == "proposal.unknown_slot"
    assert err(first.state, Accept(BOR, SAT)) == "proposal.already_answered"
    assert transition(first.state, Accept(EVE, SAT), NOW).state.status == "scheduled"


def test_not_for_me_archives_from_any_open_state_and_closes_the_proposal():
    r = transition(pending(), NotForMe(BOR), NOW)

    assert (r.state.status, r.state.proposal, r.closed, r.event) == ("archived", None, ((7, "cancelled"),), "not_for_me")
    assert transition(idea(), NotForMe(ANA), NOW).state.status == "archived"


def test_archived_idea_can_be_reopened():
    archived = IdeaState(status="archived", participants=COUPLE)

    assert transition(archived, Reopen(BOR), NOW).state.status == "idea"
    assert err(idea(), Reopen(BOR)) == "proposal.invalid_state"
