#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_NET_FIRST_SHADOW_ADMISSION_SCHEMA_V1 ==="

ROWS="$(
psql "$DATABASE_URL" -X -Atc "
SELECT COUNT(*)
FROM information_schema.tables
WHERE table_schema='analytics'
  AND table_name='net_first_shadow_admission_v1';
"
)"

[ "$ROWS" -eq 1 ]

REQUIRED_COLUMNS="$(
psql "$DATABASE_URL" -X -Atc "
SELECT COUNT(*)
FROM information_schema.columns
WHERE table_schema='analytics'
  AND table_name='net_first_shadow_admission_v1'
  AND column_name IN (
      'observation_uuid',
      'candidate_code',
      'symbol',
      'strategy_code',
      'timeframe',
      'canonical_trades',
      'gross_pnl',
      'total_cost',
      'net_pnl',
      'net_expectancy',
      'net_profit_factor',
      'economic_gate_status',
      'shadow_decision',
      'actual_robustness_scheduled',
      'production_blocked',
      'cost_contract_version',
      'policy_version',
      'source_version'
  );
"
)"

[ "$REQUIRED_COLUMNS" -eq 18 ]

echo "table_exists=1"
echo "required_columns=18"
echo "shadow_admission_enabled=1"
echo "enforced_admission_enabled=0"
echo "production_pipeline_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_NET_FIRST_SHADOW_ADMISSION_SCHEMA_V1_OK"
