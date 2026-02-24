CREATE TABLE IF NOT EXISTS snapshots (
    stream TEXT PRIMARY KEY,
    version BIGINT NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);