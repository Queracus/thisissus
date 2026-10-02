CREATE TABLE users (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    display_name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    disabled_at timestamptz
);

CREATE TABLE passkeys (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES users ON DELETE CASCADE,
    credential_id bytea NOT NULL UNIQUE,
    public_key bytea NOT NULL,
    sign_count bigint NOT NULL DEFAULT 0,
    transports text[] NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Only sha256 of the cookie token is stored.
CREATE TABLE sessions (
    token_hash bytea PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES users ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    user_agent text
);
CREATE INDEX sessions_user_idx ON sessions (user_id);

-- One-time links (invite, recovery); only sha256 of the token is stored.
CREATE TABLE auth_tokens (
    token_hash bytea PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('invite', 'recovery')),
    user_id bigint NOT NULL REFERENCES users ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    used_at timestamptz
);

-- WebAuthn challenges, consumed once.
CREATE TABLE auth_challenges (
    challenge bytea PRIMARY KEY,
    purpose text NOT NULL CHECK (purpose IN ('register', 'login')),
    user_id bigint REFERENCES users ON DELETE CASCADE,
    expires_at timestamptz NOT NULL
);
