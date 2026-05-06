CREATE TABLE IF NOT EXISTS order_events (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    state TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL DEFAULT 0,
    filled_qty DOUBLE PRECISION NOT NULL DEFAULT 0,
    remaining_qty DOUBLE PRECISION NOT NULL DEFAULT 0,
    fill_price DOUBLE PRECISION,
    avg_fill_price DOUBLE PRECISION,
    reason TEXT,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_order_events_order_id ON order_events(order_id);
CREATE INDEX IF NOT EXISTS idx_order_events_symbol ON order_events(symbol);
CREATE INDEX IF NOT EXISTS idx_order_events_ts ON order_events(ts DESC);
