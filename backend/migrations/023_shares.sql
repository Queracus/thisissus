-- Read-only shares: one item or a whole section (all dates/ideas/recipes of a space),
-- to an account (target_user_id) or via a secret link (token_hash, #31).
CREATE TABLE shares (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    space_id bigint NOT NULL REFERENCES spaces ON DELETE CASCADE,
    created_by bigint REFERENCES users ON DELETE SET NULL,
    scope text NOT NULL CHECK (scope IN ('item', 'section')),
    entity_type text NOT NULL CHECK (entity_type IN ('date', 'idea', 'recipe')),
    entity_id bigint,
    target_user_id bigint REFERENCES users ON DELETE CASCADE,
    token_hash bytea UNIQUE,
    expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    CHECK ((scope = 'item') = (entity_id IS NOT NULL)),
    CHECK ((target_user_id IS NULL) <> (token_hash IS NULL))
);
CREATE INDEX shares_target_idx ON shares (target_user_id) WHERE revoked_at IS NULL;
CREATE INDEX shares_space_idx ON shares (space_id) WHERE revoked_at IS NULL;
