-- Each partner's own view of a date.
CREATE TABLE date_reviews (
    date_id bigint NOT NULL REFERENCES dates ON DELETE CASCADE,
    user_id bigint NOT NULL REFERENCES users ON DELETE CASCADE,
    rating smallint NOT NULL CHECK (rating BETWEEN 1 AND 5),
    again text NOT NULL CHECK (again IN ('yes', 'maybe', 'no')),
    notes text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (date_id, user_id)
);
