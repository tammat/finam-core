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
  ('GDM6@RTSX', 'metals_gold', true, 'gold futures intermarket monitoring'),
  ('GDU6@RTSX', 'metals_gold', true, 'gold futures intermarket monitoring'),
  ('GLM6@RTSX', 'metals_gold', true, 'gold futures intermarket monitoring'),
  ('GLU6@RTSX', 'metals_gold', true, 'gold futures intermarket monitoring'),
  ('SVM6@RTSX', 'metals_silver', true, 'silver futures intermarket monitoring'),
  ('SVU6@RTSX', 'metals_silver', true, 'silver futures intermarket monitoring')
ON CONFLICT (symbol) DO UPDATE
SET
    asset_group = EXCLUDED.asset_group,
    is_enabled = EXCLUDED.is_enabled,
    reason = EXCLUDED.reason,
    updated_at = now();
SQL

echo "SEED_METALS_WATCH_UNIVERSE_V1_OK"
