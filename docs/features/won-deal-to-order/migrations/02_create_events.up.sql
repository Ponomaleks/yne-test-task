-- One row per HubSpot event ID; the primary key makes a repeated event a no-op on INSERT OR IGNORE.
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY,
    deal_id TEXT NOT NULL,
    subscription_type TEXT NOT NULL,
    property_name TEXT,
    received_at INTEGER NOT NULL
);
