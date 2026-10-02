-- PIN fallback login: username + 6-digit PIN (argon2 hash).
ALTER TABLE users ADD COLUMN username text, ADD COLUMN pin_hash text;
CREATE UNIQUE INDEX users_username_idx ON users (lower(username));

-- Failed-login throttle, one row per key ('user:<id>' or 'ip:<addr>').
CREATE TABLE login_throttle (
    key text PRIMARY KEY,
    failures int NOT NULL DEFAULT 0,
    level int NOT NULL DEFAULT 0,      -- how many locks so far (escalation)
    locked_until timestamptz
);
