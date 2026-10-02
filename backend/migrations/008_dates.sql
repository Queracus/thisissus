-- Dates We've Had. Soft delete via deleted_at (trash, purged after 30 days).
CREATE TABLE dates (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    space_id bigint NOT NULL REFERENCES spaces ON DELETE CASCADE,
    title text NOT NULL,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz CHECK (ends_at >= starts_at),
    place_name text,
    lat double precision CHECK (lat BETWEEN -90 AND 90),
    lon double precision CHECK (lon BETWEEN -180 AND 180),
    cost numeric(10, 2) CHECK (cost >= 0),
    created_by bigint REFERENCES users ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz
);
CREATE INDEX dates_space_idx ON dates (space_id, starts_at DESC) WHERE deleted_at IS NULL;
