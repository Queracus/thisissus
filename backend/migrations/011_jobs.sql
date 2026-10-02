-- Background jobs: claimed with FOR UPDATE SKIP LOCKED, retried with backoff, given up after N attempts.
CREATE TABLE jobs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}',
    run_at timestamptz NOT NULL DEFAULT now(),
    attempts int NOT NULL DEFAULT 0,
    locked_until timestamptz,
    done_at timestamptz,
    failed_at timestamptz,
    last_error text,
    dedupe_key text UNIQUE,            -- periodic jobs: one per kind and period
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX jobs_due_idx ON jobs (run_at) WHERE done_at IS NULL AND failed_at IS NULL;
