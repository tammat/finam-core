#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS feature_snapshots (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    root_symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,

    close NUMERIC(20,8) NOT NULL DEFAULT 0,
    return_1 NUMERIC(20,8) NOT NULL DEFAULT 0,
    return_n NUMERIC(20,8) NOT NULL DEFAULT 0,
    atr_proxy NUMERIC(20,8) NOT NULL DEFAULT 0,

    volatility_state TEXT NOT NULL DEFAULT 'unknown',
    trend_state TEXT NOT NULL DEFAULT 'unknown',
    range_state TEXT NOT NULL DEFAULT 'unknown',
    session_state TEXT NOT NULL DEFAULT 'unknown',

    intermarket_risk_mode TEXT NOT NULL DEFAULT 'unknown',
    intermarket_commodity_mode TEXT NOT NULL DEFAULT 'unknown',
    fx_stress_score NUMERIC(20,8) NOT NULL DEFAULT 0,
    commodity_score NUMERIC(20,8) NOT NULL DEFAULT 0,

    quality TEXT NOT NULL DEFAULT 'PARTIAL',
    reason TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(symbol, timeframe, ts)
);

CREATE INDEX IF NOT EXISTS idx_feature_snapshots_symbol_tf_ts
ON feature_snapshots(symbol, timeframe, ts DESC);

CREATE INDEX IF NOT EXISTS idx_feature_snapshots_root_tf_ts
ON feature_snapshots(root_symbol, timeframe, ts DESC);

CREATE INDEX IF NOT EXISTS idx_feature_snapshots_context
ON feature_snapshots(root_symbol, timeframe, volatility_state, trend_state, range_state);
SQL

echo "FEATURE_SNAPSHOTS_V1_MIGRATION_OK"
