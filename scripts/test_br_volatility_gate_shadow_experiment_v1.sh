#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_SHADOW_EXPERIMENT_V1 ==="

src/scripts/research/build_br_volatility_gate_shadow_experiment_v1.py \
  --symbol BRN6@RTSX \
  --lookback-hours 2 \
  --shadow-threshold 0.0004 \
  --save \
  | tee /tmp/br_volatility_gate_shadow_experiment_v1.out

grep -q "BR_VOLATILITY_GATE_SHADOW_EXPERIMENT_V1" /tmp/br_volatility_gate_shadow_experiment_v1.out
grep -q "mode=save" /tmp/br_volatility_gate_shadow_experiment_v1.out
grep -q "symbol=BRN6@RTSX" /tmp/br_volatility_gate_shadow_experiment_v1.out
grep -q "runtime_changed=0" /tmp/br_volatility_gate_shadow_experiment_v1.out
grep -q "execution_changed=0" /tmp/br_volatility_gate_shadow_experiment_v1.out
grep -q "orders_changed=0" /tmp/br_volatility_gate_shadow_experiment_v1.out
grep -q "fills_changed=0" /tmp/br_volatility_gate_shadow_experiment_v1.out
grep -q "micro_live_allowed=0" /tmp/br_volatility_gate_shadow_experiment_v1.out
grep -q "VERDICT=BR_VOLATILITY_GATE_SHADOW_EXPERIMENT_READY" /tmp/br_volatility_gate_shadow_experiment_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'table_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='br_volatility_gate_shadow_observation_v1'
);

SELECT 'rows_total=' || count(*)
FROM research.br_volatility_gate_shadow_observation_v1;

SELECT 'latest_symbol=' || symbol
FROM research.br_volatility_gate_shadow_observation_v1
ORDER BY created_at DESC
LIMIT 1;

SELECT 'latest_shadow_decision=' || shadow_decision
FROM research.br_volatility_gate_shadow_observation_v1
ORDER BY created_at DESC
LIMIT 1;
SQL

echo "TEST_BR_VOLATILITY_GATE_SHADOW_EXPERIMENT_V1_OK"
