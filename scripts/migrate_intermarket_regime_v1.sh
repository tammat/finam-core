#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS intermarket_regime_snapshots (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    timeframe TEXT NOT NULL,
    br_score NUMERIC(20,8) NOT NULL DEFAULT 0,
    ng_score NUMERIC(20,8) NOT NULL DEFAULT 0,
    gold_score NUMERIC(20,8) NOT NULL DEFAULT 0,
    silver_score NUMERIC(20,8) NOT NULL DEFAULT 0,
    usdrub_score NUMERIC(20,8) NOT NULL DEFAULT 0,
    cny_score NUMERIC(20,8) NOT NULL DEFAULT 0,
    commodity_score NUMERIC(20,8) NOT NULL DEFAULT 0,
    fx_stress_score NUMERIC(20,8) NOT NULL DEFAULT 0,
    risk_mode TEXT NOT NULL,
    commodity_mode TEXT NOT NULL,
    confidence NUMERIC(20,8) NOT NULL DEFAULT 0,
    reason TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intermarket_regime_snapshots_ts
ON intermarket_regime_snapshots(ts DESC);

CREATE INDEX IF NOT EXISTS idx_intermarket_regime_snapshots_timeframe
ON intermarket_regime_snapshots(timeframe, ts DESC);
SQL

echo "INTERMARKET_REGIME_V1_MIGRATION_OK"
