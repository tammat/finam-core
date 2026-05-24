#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
ALTER TABLE runtime_regime_overrides
ADD COLUMN IF NOT EXISTS is_default_policy BOOLEAN NOT NULL DEFAULT false;

UPDATE runtime_regime_overrides
SET is_default_policy = (runtime_action = 'NEUTRAL');
SQL

echo "RUNTIME_REGIME_OVERRIDES_DEFAULT_POLICY_MIGRATION_OK"
