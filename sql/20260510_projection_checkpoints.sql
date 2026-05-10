CREATE TABLE IF NOT EXISTS projection_checkpoints (
    name TEXT PRIMARY KEY,
    last_event_id BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
