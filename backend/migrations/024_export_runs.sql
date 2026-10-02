-- Results of media exports (shown in the admin panel).
CREATE TABLE export_runs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    finished_at timestamptz NOT NULL DEFAULT now(),
    files int NOT NULL,
    written int NOT NULL
);
