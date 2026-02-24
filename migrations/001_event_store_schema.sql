CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY,
    stream TEXT NOT NULL,
    type TEXT NOT NULL,
    version BIGINT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_events_stream_version
ON events(stream, version);