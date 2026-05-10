CREATE TABLE IF NOT EXISTS event_store (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    aggregate_type TEXT NOT NULL DEFAULT 'system',
    aggregate_id TEXT,
    source TEXT NOT NULL DEFAULT 'system',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_event_store_event_type
ON event_store(event_type);

CREATE INDEX IF NOT EXISTS idx_event_store_aggregate
ON event_store(aggregate_type, aggregate_id);

CREATE INDEX IF NOT EXISTS idx_event_store_created_at
ON event_store(created_at);
