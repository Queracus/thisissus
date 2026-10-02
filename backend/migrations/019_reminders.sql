-- Reminders already sent (so the hourly tick never repeats one). key = kind:ref:version, e.g. date.tomorrow:12:2026-10-03T19:00Z
CREATE TABLE reminders_sent (
    key text NOT NULL,
    user_id bigint NOT NULL REFERENCES users ON DELETE CASCADE,
    sent_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (key, user_id)
);
