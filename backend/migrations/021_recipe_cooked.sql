-- Each partner's recipe review, every time we cooked it, and dates that were "cooking together".
CREATE TABLE recipe_reviews (
    recipe_id bigint NOT NULL REFERENCES recipes ON DELETE CASCADE,
    user_id bigint NOT NULL REFERENCES users ON DELETE CASCADE,
    rating smallint NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (recipe_id, user_id)
);

CREATE TABLE recipe_cooks (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recipe_id bigint NOT NULL REFERENCES recipes ON DELETE CASCADE,
    date_id bigint REFERENCES dates ON DELETE SET NULL,
    created_by bigint REFERENCES users ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX recipe_cooks_recipe_idx ON recipe_cooks (recipe_id, created_at DESC);

ALTER TABLE dates ADD COLUMN recipe_id bigint REFERENCES recipes ON DELETE SET NULL;
