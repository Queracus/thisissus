-- Media lives in Postgres (one dump = complete backup), split into chunks so ranges stream without loading whole files.
CREATE TABLE media (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    space_id bigint NOT NULL REFERENCES spaces ON DELETE CASCADE,
    parent_id bigint REFERENCES media ON DELETE CASCADE,          -- derivatives point at their original
    kind text NOT NULL CHECK (kind IN ('photo', 'video')),
    variant text NOT NULL CHECK (variant IN ('original', 'display', 'thumb', 'mp4', 'poster')),
    mime text NOT NULL,
    size bigint NOT NULL DEFAULT 0,
    chunk_size int NOT NULL,
    sha256 bytea,
    width int,
    height int,
    duration_s real,
    exif jsonb,                                                   -- parsed from the original only; never served in shares
    status text NOT NULL DEFAULT 'ready' CHECK (status IN ('pending', 'ready', 'failed')),
    created_by bigint REFERENCES users ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz
);
CREATE INDEX media_parent_idx ON media (parent_id, variant);

CREATE TABLE media_chunks (
    media_id bigint NOT NULL REFERENCES media ON DELETE CASCADE,
    seq int NOT NULL,
    data bytea NOT NULL,
    PRIMARY KEY (media_id, seq)
);
-- Photos/videos are already compressed: skip TOAST compression attempts.
ALTER TABLE media_chunks ALTER COLUMN data SET STORAGE EXTERNAL;

CREATE TABLE date_media (
    date_id bigint NOT NULL REFERENCES dates ON DELETE CASCADE,
    media_id bigint NOT NULL REFERENCES media ON DELETE CASCADE,
    caption text,
    position int NOT NULL,
    PRIMARY KEY (date_id, media_id)
);
