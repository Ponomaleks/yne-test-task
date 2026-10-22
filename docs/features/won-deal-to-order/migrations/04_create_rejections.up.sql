-- Deliveries rejected by the signature check: technical identity only.
CREATE TABLE IF NOT EXISTS rejections (
    id INTEGER PRIMARY KEY,
    request_timestamp TEXT,
    body_sha256 TEXT NOT NULL,
    reason TEXT NOT NULL,
    received_at INTEGER NOT NULL
);
