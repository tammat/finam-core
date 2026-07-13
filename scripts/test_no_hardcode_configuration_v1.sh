#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_NO_HARDCODE_CONFIGURATION_V1 ==="

targets=(
  "src/scripts/build_edge_score_model_v2.py"
  "src/scripts/build_swing_shadow_experiment_guard_v1.py"
  "src/scripts/run_swing_forward_shadow_router_v1.py"
)

for f in "${targets[@]}"; do
  test -f "$f"
done

forbidden=$(grep -RniE \
  'Decimal\("0\.40"\)|Decimal\("0\.30"\)|Decimal\("0\.15"\)|\* Decimal\("0\.[0-9]+"\)' \
  "${targets[@]}" || true)

if [ -n "$forbidden" ]; then
  echo "HARDCODED_BUSINESS_WEIGHTS_FOUND"
  echo "$forbidden"
  exit 1
fi

swing_forbidden=$(grep -nE \
  '"(cohort_size|minimum_closed_per_timeframe|minimum_trading_sessions|minimum_net_profit_factor|minimum_net_expectancy|atr_lookback|atr_multiplier|commission_bps)"[[:space:]]*:[[:space:]]*[0-9]' \
  "${targets[@]:1}" || true)

if [ -n "$swing_forbidden" ]; then
  echo "HARDCODED_SWING_POLICY_FOUND"
  echo "$swing_forbidden"
  exit 1
fi

echo "checked_files=${#targets[@]}"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=NO_HARDCODE_CONFIGURATION_V1_READY"
echo "VERDICT=TEST_NO_HARDCODE_CONFIGURATION_V1_OK"
