-- Date Ideas: a wishlist; proposals/scheduling (#19+) move an idea through idea → pending → scheduled.
CREATE TABLE ideas (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    space_id bigint NOT NULL REFERENCES spaces ON DELETE CASCADE,
    title text NOT NULL,
    description text,
    url text,
    est_cost numeric(10, 2) CHECK (est_cost >= 0),
    season text CHECK (season IN ('spring', 'summer', 'autumn', 'winter')),
    status text NOT NULL DEFAULT 'idea' CHECK (status IN ('idea', 'pending', 'scheduled', 'archived')),
    scheduled_at timestamptz,
    times_done int NOT NULL DEFAULT 0,
    suggested_by bigint REFERENCES users ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz
);
CREATE INDEX ideas_space_idx ON ideas (space_id, created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE idea_tags (
    idea_id bigint NOT NULL REFERENCES ideas ON DELETE CASCADE,
    tag_id bigint NOT NULL REFERENCES tags ON DELETE CASCADE,
    PRIMARY KEY (idea_id, tag_id)
);
