-- Public id for listing/revoking sessions without exposing the token hash.
ALTER TABLE sessions ADD COLUMN id bigint GENERATED ALWAYS AS IDENTITY UNIQUE;
