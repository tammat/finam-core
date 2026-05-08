CREATE TABLE IF NOT EXISTS real_position_snapshots (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_price DOUBLE PRECISION,
    market_price DOUBLE PRECISION,
    unrealized_pnl DOUBLE PRECISION,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_real_position_snapshots_symbol_ts
    ON real_position_snapshots (symbol, ts DESC);
