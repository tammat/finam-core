#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO market_data_watch_universe (
    symbol,
    asset_group,
    is_enabled,
    reason
)
VALUES
  ('CNYRUBF@RTSX', 'fx_cny', true, 'yuan futures intermarket monitoring'),
  ('CNYRUB_TOM@MISX', 'fx_cny', true, 'yuan TOM intermarket monitoring')
ON CONFLICT (symbol) DO UPDATE
SET
    asset_group = EXCLUDED.asset_group,
    is_enabled = EXCLUDED.is_enabled,
    reason = EXCLUDED.reason,
    updated_at = now();
SQL

echo "SEED_YUAN_WATCH_UNIVERSE_V1_OK"
