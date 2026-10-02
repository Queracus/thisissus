-- Spaces own all content. Users can be in several spaces.
CREATE TABLE spaces (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE space_members (
    space_id bigint NOT NULL REFERENCES spaces ON DELETE CASCADE,
    user_id bigint NOT NULL REFERENCES users ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('owner', 'member')),
    joined_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (space_id, user_id)
);
CREATE INDEX space_members_user_idx ON space_members (user_id);

-- Invites can join a space; 'space_invite' is for existing users (no user_id).
ALTER TABLE auth_tokens ADD COLUMN space_id bigint REFERENCES spaces ON DELETE CASCADE;
ALTER TABLE auth_tokens ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE auth_tokens DROP CONSTRAINT auth_tokens_kind_check;
ALTER TABLE auth_tokens ADD CONSTRAINT auth_tokens_kind_check CHECK (kind IN ('invite', 'recovery', 'space_invite'));
ALTER TABLE auth_tokens ADD CONSTRAINT auth_tokens_target_check CHECK ((kind = 'space_invite') = (user_id IS NULL));
