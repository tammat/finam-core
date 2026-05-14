#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
ALTER TABLE strategy_runtime_control
ADD COLUMN IF NOT EXISTS strategy TEXT NOT NULL DEFAULT 'default';

DROP INDEX IF EXISTS strategy_runtime_control_symbol_key;

ALTER TABLE strategy_runtime_control
DROP CONSTRAINT IF EXISTS strategy_runtime_control_symbol_key;

CREATE UNIQUE INDEX IF NOT EXISTS ux_strategy_runtime_control_symbol_strategy
ON strategy_runtime_control(symbol, strategy);

CREATE INDEX IF NOT EXISTS idx_strategy_runtime_control_symbol_strategy_status
ON strategy_runtime_control(symbol, strategy, status);
SQL

echo "OK: strategy_runtime_control migrated to symbol+strategy"
