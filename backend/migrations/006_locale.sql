ALTER TABLE users ADD COLUMN locale text NOT NULL DEFAULT 'sl' CHECK (locale IN ('sl', 'en'));
