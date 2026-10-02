-- "We did it!": a date can come from an idea; a proposal ends as 'done'.
ALTER TABLE dates ADD COLUMN idea_id bigint REFERENCES ideas ON DELETE SET NULL;
ALTER TABLE proposals DROP CONSTRAINT proposals_status_check;
ALTER TABLE proposals ADD CONSTRAINT proposals_status_check CHECK (status IN ('open', 'accepted', 'superseded', 'refused', 'cancelled', 'done'));
