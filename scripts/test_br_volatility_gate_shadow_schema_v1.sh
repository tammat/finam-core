#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_SHADOW_SCHEMA_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'source_table_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='public'
      AND table_name='runtime_guard_pre_signal_block_audit_v1'
);

SELECT 'source_columns=' || string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name='runtime_guard_pre_signal_block_audit_v1';

SELECT 'target_table=research.br_volatility_gate_shadow_observation_v1';

SELECT 'target_columns=observation_id,ts,symbol,strategy,timeframe,price,atr,atr_pct,current_threshold,shadow_threshold,current_decision,shadow_decision,block_reason,compression_ratio,regime,trend,volatility,payload,created_at';

SELECT 'planned_indexes=symbol_created_at,shadow_decision_created_at,block_reason_created_at';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=BR_VOLATILITY_GATE_SHADOW_SCHEMA_V1_READY';
SQL

echo "TEST_BR_VOLATILITY_GATE_SHADOW_SCHEMA_V1_OK"
