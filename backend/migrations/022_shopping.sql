-- Shared shopping list per space.
CREATE TABLE shopping_items (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    space_id bigint NOT NULL REFERENCES spaces ON DELETE CASCADE,
    item text NOT NULL,
    amount numeric(10, 3),
    unit text,
    recipe_id bigint REFERENCES recipes ON DELETE SET NULL,
    checked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX shopping_space_idx ON shopping_items (space_id);
