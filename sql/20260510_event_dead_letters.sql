CREATE TABLE IF NOT EXISTS event_dead_letters (
    id BIGSERIAL PRIMARY KEY,
    event_db_id BIGINT,
    event_id TEXT,
    event_type TEXT,
    aggregate_type TEXT,
    aggregate_id TEXT,
    source TEXT NOT NULL DEFAULT 'system',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    worker_name TEXT NOT NULL DEFAULT 'unknown',
    resolved BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_event_dead_letters_event_id
ON event_dead_letters(event_id);

CREATE INDEX IF NOT EXISTS idx_event_dead_letters_resolved
ON event_dead_letters(resolved);

CREATE INDEX IF NOT EXISTS idx_event_dead_letters_created_at
ON event_dead_letters(created_at);
