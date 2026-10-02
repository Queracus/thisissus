-- Recipes: our cookbook. Want to try → cooked.
CREATE TABLE recipes (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    space_id bigint NOT NULL REFERENCES spaces ON DELETE CASCADE,
    title text NOT NULL,
    portions int NOT NULL DEFAULT 2 CHECK (portions >= 1),
    prep_minutes int CHECK (prep_minutes >= 0),
    source_url text,
    status text NOT NULL DEFAULT 'want' CHECK (status IN ('want', 'cooked')),
    created_by bigint REFERENCES users ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz
);
CREATE INDEX recipes_space_idx ON recipes (space_id, created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE recipe_ingredients (
    recipe_id bigint NOT NULL REFERENCES recipes ON DELETE CASCADE,
    position int NOT NULL,
    amount numeric(10, 3),          -- NULL = "to taste"
    unit text,
    item text NOT NULL,
    PRIMARY KEY (recipe_id, position)
);

CREATE TABLE recipe_steps (
    recipe_id bigint NOT NULL REFERENCES recipes ON DELETE CASCADE,
    position int NOT NULL,
    text text NOT NULL,
    PRIMARY KEY (recipe_id, position)
);

CREATE TABLE recipe_tags (
    recipe_id bigint NOT NULL REFERENCES recipes ON DELETE CASCADE,
    tag_id bigint NOT NULL REFERENCES tags ON DELETE CASCADE,
    PRIMARY KEY (recipe_id, tag_id)
);

CREATE TABLE recipe_media (
    recipe_id bigint NOT NULL REFERENCES recipes ON DELETE CASCADE,
    media_id bigint NOT NULL REFERENCES media ON DELETE CASCADE,
    caption text,
    position int NOT NULL,
    PRIMARY KEY (recipe_id, media_id)
);
