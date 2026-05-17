CREATE TABLE IF NOT EXISTS runtime_worker_state (
    symbol TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NULL,
    stopped_at TIMESTAMPTZ NULL,
    last_heartbeat_at TIMESTAMPTZ NULL,
    last_error TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
