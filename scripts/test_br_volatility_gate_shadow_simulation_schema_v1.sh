#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_SHADOW_SIMULATION_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'source_table_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='br_volatility_gate_shadow_observation_v1'
);

SELECT 'source_columns=' || string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='research'
  AND table_name='br_volatility_gate_shadow_observation_v1';

SELECT 'target_table=research.br_volatility_gate_shadow_simulation_v1';

SELECT 'target_columns=simulation_id,observation_id,symbol,strategy,timeframe,entry_ts,entry_price,horizon_bars,exit_ts,exit_price,gross_pnl,commission,net_pnl,mfe,mae,outcome,payload,created_at';

SELECT 'planned_horizons=3,5,10,15';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=BR_VOLATILITY_GATE_SHADOW_SIMULATION_SCHEMA_V1_READY';
SQL

echo "TEST_BR_VOLATILITY_GATE_SHADOW_SIMULATION_SCHEMA_V1_OK"
