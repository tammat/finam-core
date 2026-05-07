CREATE TABLE IF NOT EXISTS execution_events (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type TEXT NOT NULL,
    symbol TEXT,
    side TEXT,
    qty DOUBLE PRECISION,
    price DOUBLE PRECISION,
    status TEXT,
    reason TEXT,
    order_id TEXT,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_execution_events_ts
    ON execution_events (ts DESC);

CREATE INDEX IF NOT EXISTS idx_execution_events_symbol_ts
    ON execution_events (symbol, ts DESC);

CREATE INDEX IF NOT EXISTS idx_execution_events_event_type_ts
    ON execution_events (event_type, ts DESC);
