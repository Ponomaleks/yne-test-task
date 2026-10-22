-- Applied at startup by app.store.init_store. Only CREATE ... IF NOT EXISTS statements,
-- so applying it again is a no-op. Feature tables come from design/data-model.
PRAGMA user_version = 1;

-- Accepted deliveries (valid signature), written before the acknowledgement. No body is stored.
CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY,
    request_timestamp INTEGER NOT NULL,
    body_sha256 TEXT NOT NULL,
    event_count INTEGER NOT NULL CHECK (event_count >= 0),
    received_at INTEGER NOT NULL
);

-- One row per HubSpot event ID; the primary key makes a repeated event a no-op on INSERT OR IGNORE.
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY,
    deal_id TEXT NOT NULL,
    subscription_type TEXT NOT NULL,
    property_name TEXT,
    received_at INTEGER NOT NULL
);

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

-- Deliveries rejected by the signature check: technical identity only.
CREATE TABLE IF NOT EXISTS rejections (
    id INTEGER PRIMARY KEY,
    request_timestamp TEXT,
    body_sha256 TEXT NOT NULL,
    reason TEXT NOT NULL,
    received_at INTEGER NOT NULL
);
