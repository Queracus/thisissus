-- Who is invited to an idea. No rows = everyone in the space (the default).
CREATE TABLE idea_invitees (
    idea_id bigint NOT NULL REFERENCES ideas ON DELETE CASCADE,
    user_id bigint NOT NULL REFERENCES users ON DELETE CASCADE,
    PRIMARY KEY (idea_id, user_id)
);
