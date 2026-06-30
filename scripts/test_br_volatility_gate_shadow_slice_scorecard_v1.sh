#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_SHADOW_SLICE_SCORECARD_V1 ==="

src/scripts/research/build_br_volatility_gate_shadow_slice_scorecard_v1.py \
  --symbol BRN6@RTSX \
  | tee /tmp/br_volatility_gate_shadow_slice_scorecard_v1.out

grep -q "BR_VOLATILITY_GATE_SHADOW_SLICE_SCORECARD_V1" /tmp/br_volatility_gate_shadow_slice_scorecard_v1.out
grep -q "symbol=BRN6@RTSX" /tmp/br_volatility_gate_shadow_slice_scorecard_v1.out
grep -q "best_slice=" /tmp/br_volatility_gate_shadow_slice_scorecard_v1.out
grep -q "runtime_changed=0" /tmp/br_volatility_gate_shadow_slice_scorecard_v1.out
grep -q "execution_changed=0" /tmp/br_volatility_gate_shadow_slice_scorecard_v1.out
grep -q "orders_changed=0" /tmp/br_volatility_gate_shadow_slice_scorecard_v1.out
grep -q "fills_changed=0" /tmp/br_volatility_gate_shadow_slice_scorecard_v1.out
grep -q "micro_live_allowed=0" /tmp/br_volatility_gate_shadow_slice_scorecard_v1.out
grep -q "VERDICT=BR_VOLATILITY_GATE_SHADOW_SLICE_SCORECARD_READY" /tmp/br_volatility_gate_shadow_slice_scorecard_v1.out

echo "TEST_BR_VOLATILITY_GATE_SHADOW_SLICE_SCORECARD_V1_OK"
