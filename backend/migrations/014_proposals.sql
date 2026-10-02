-- Time proposals for ideas (state machine in app/proposals.py) and the idea timeline.
CREATE TABLE proposals (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    idea_id bigint NOT NULL REFERENCES ideas ON DELETE CASCADE,
    proposed_by bigint REFERENCES users ON DELETE SET NULL,
    status text NOT NULL CHECK (status IN ('open', 'accepted', 'superseded', 'refused', 'cancelled')),
    created_at timestamptz NOT NULL DEFAULT now()
);
-- At most one live (open/accepted) proposal per idea.
CREATE UNIQUE INDEX proposals_live_idx ON proposals (idea_id) WHERE status IN ('open', 'accepted');

CREATE TABLE proposal_slots (
    proposal_id bigint NOT NULL REFERENCES proposals ON DELETE CASCADE,
    starts_at timestamptz NOT NULL,
    PRIMARY KEY (proposal_id, starts_at)
);

CREATE TABLE proposal_responses (
    proposal_id bigint NOT NULL REFERENCES proposals ON DELETE CASCADE,
    user_id bigint NOT NULL REFERENCES users ON DELETE CASCADE,
    starts_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (proposal_id, user_id)
);

CREATE TABLE idea_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    idea_id bigint NOT NULL REFERENCES ideas ON DELETE CASCADE,
    actor_id bigint REFERENCES users ON DELETE SET NULL,
    kind text NOT NULL,             -- proposed | countered | accepted | scheduled | refused | cancelled | comment | ...
    payload jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX idea_events_idea_idx ON idea_events (idea_id, id);
