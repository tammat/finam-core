#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_SHADOW_SIMULATION_V1 ==="

src/scripts/research/build_br_volatility_gate_shadow_simulation_v1.py \
  --symbol BRN6@RTSX \
  --horizons 3,5,10,15 \
  --save \
  | tee /tmp/br_volatility_gate_shadow_simulation_v1.out

grep -q "BR_VOLATILITY_GATE_SHADOW_SIMULATION_V1" /tmp/br_volatility_gate_shadow_simulation_v1.out
grep -q "mode=save" /tmp/br_volatility_gate_shadow_simulation_v1.out
grep -q "symbol=BRN6@RTSX" /tmp/br_volatility_gate_shadow_simulation_v1.out
grep -q "runtime_changed=0" /tmp/br_volatility_gate_shadow_simulation_v1.out
grep -q "execution_changed=0" /tmp/br_volatility_gate_shadow_simulation_v1.out
grep -q "orders_changed=0" /tmp/br_volatility_gate_shadow_simulation_v1.out
grep -q "fills_changed=0" /tmp/br_volatility_gate_shadow_simulation_v1.out
grep -q "micro_live_allowed=0" /tmp/br_volatility_gate_shadow_simulation_v1.out
grep -q "VERDICT=BR_VOLATILITY_GATE_SHADOW_SIMULATION_READY" /tmp/br_volatility_gate_shadow_simulation_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'table_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='br_volatility_gate_shadow_simulation_v1'
);

SELECT 'simulation_rows=' || count(*)
FROM research.br_volatility_gate_shadow_simulation_v1
WHERE symbol='BRN6@RTSX';

SELECT 'side_rows=' || side || '|' || count(*)
FROM research.br_volatility_gate_shadow_simulation_v1
WHERE symbol='BRN6@RTSX'
GROUP BY side
ORDER BY side;

SELECT 'horizon_rows=' || horizon_bars || '|' || count(*)
FROM research.br_volatility_gate_shadow_simulation_v1
WHERE symbol='BRN6@RTSX'
GROUP BY horizon_bars
ORDER BY horizon_bars;
SQL

echo "TEST_BR_VOLATILITY_GATE_SHADOW_SIMULATION_V1_OK"
