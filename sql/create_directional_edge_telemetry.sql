CREATE TABLE IF NOT EXISTS directional_edge_telemetry (
    id BIGSERIAL PRIMARY KEY,

    ts TIMESTAMPTZ NOT NULL DEFAULT now(),

    symbol TEXT NOT NULL,
    continuous_symbol TEXT NOT NULL,

    strategy TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    trade_source TEXT NOT NULL DEFAULT 'paper',

    side TEXT NOT NULL,
    regime_direction TEXT NOT NULL,

    advisory_status TEXT NOT NULL,
    advisory_reason TEXT NOT NULL,

    guard_status TEXT,
    guard_mode TEXT NOT NULL,

    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_directional_edge_telemetry_ts
ON directional_edge_telemetry(ts DESC);

CREATE INDEX IF NOT EXISTS idx_directional_edge_telemetry_symbol
ON directional_edge_telemetry(symbol, strategy, timeframe);

CREATE INDEX IF NOT EXISTS idx_directional_edge_telemetry_regime
ON directional_edge_telemetry(regime_direction, advisory_status);
