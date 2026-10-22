-- Append-only: one row per processing attempt; the highest id is the event's outcome.
CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events (event_id),
    deal_id TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('ordered', 'skipped', 'held', 'failed')),
    reason TEXT NOT NULL,
    dry_run INTEGER NOT NULL CHECK (dry_run IN (0, 1)),
    recorded_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_outcomes_event_id ON outcomes (event_id);
