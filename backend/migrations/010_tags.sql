-- Tags per space, shared by dates (now), ideas and recipes (later).
-- Starter tags have a starter_key the frontend translates; custom tags show their name.
CREATE TABLE tags (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    space_id bigint NOT NULL REFERENCES spaces ON DELETE CASCADE,
    name text NOT NULL,
    starter_key text
);
CREATE UNIQUE INDEX tags_space_name_idx ON tags (space_id, lower(name));

CREATE TABLE date_tags (
    date_id bigint NOT NULL REFERENCES dates ON DELETE CASCADE,
    tag_id bigint NOT NULL REFERENCES tags ON DELETE CASCADE,
    PRIMARY KEY (date_id, tag_id)
);

CREATE FUNCTION seed_starter_tags() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO tags (space_id, name, starter_key)
    SELECT NEW.id, k, k FROM unnest(ARRAY['food', 'outdoors', 'movie', 'cheap', 'romantic', 'culture', 'sport', 'home', 'trip']) AS k;
    RETURN NEW;
END $$;

CREATE TRIGGER spaces_starter_tags AFTER INSERT ON spaces FOR EACH ROW EXECUTE FUNCTION seed_starter_tags();

-- Existing spaces get the starter set too.
INSERT INTO tags (space_id, name, starter_key)
SELECT s.id, k, k FROM spaces s, unnest(ARRAY['food', 'outdoors', 'movie', 'cheap', 'romantic', 'culture', 'sport', 'home', 'trip']) AS k;
