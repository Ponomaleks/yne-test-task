-- Accepted deliveries (valid signature), written before the acknowledgement. No body is stored.
CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY,
    request_timestamp INTEGER NOT NULL,
    body_sha256 TEXT NOT NULL,
    event_count INTEGER NOT NULL CHECK (event_count >= 0),
    received_at INTEGER NOT NULL
);
