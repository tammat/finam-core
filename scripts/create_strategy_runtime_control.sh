#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS strategy_runtime_control (
    id BIGSERIAL PRIMARY KEY,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    symbol TEXT NOT NULL UNIQUE,

    status TEXT NOT NULL DEFAULT 'NO_DATA',
    allow_trade BOOLEAN NOT NULL DEFAULT false,
    watch_only BOOLEAN NOT NULL DEFAULT true,
    risk_multiplier DOUBLE PRECISION NOT NULL DEFAULT 0.0,

    reason TEXT,

    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_strategy_runtime_control_status
ON strategy_runtime_control(status);
SQL

echo "OK: strategy_runtime_control created"
