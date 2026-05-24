#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS runtime_regime_overrides (
    id BIGSERIAL PRIMARY KEY,

    strategy TEXT NOT NULL,
    root_symbol TEXT NOT NULL,
    regime TEXT NOT NULL,

    runtime_action TEXT NOT NULL DEFAULT 'WATCH',

    max_position_size NUMERIC(20,8) NOT NULL DEFAULT 1.0,
    allowed_execution_mode TEXT NOT NULL DEFAULT 'paper',
    risk_multiplier NUMERIC(20,8) NOT NULL DEFAULT 1.0,
    cooldown_sec INTEGER NOT NULL DEFAULT 0,
    stop_take_profile TEXT NOT NULL DEFAULT '',

    source_recommendation TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(strategy, root_symbol, regime)
);

CREATE INDEX IF NOT EXISTS idx_runtime_regime_overrides_symbol
ON runtime_regime_overrides(root_symbol, strategy);

CREATE INDEX IF NOT EXISTS idx_runtime_regime_overrides_action
ON runtime_regime_overrides(runtime_action);
SQL

echo "RUNTIME_REGIME_OVERRIDES_V3_MIGRATION_OK"
