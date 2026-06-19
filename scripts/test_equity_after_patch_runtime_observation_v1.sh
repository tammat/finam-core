#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY AFTER PATCH RUNTIME OBSERVATION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_after_patch_runtime_observation_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_after_patch_runtime_observation_v1.py \
  | tee /tmp/equity_after_patch_runtime_observation_v1.log

grep -q "EQUITY_AFTER_PATCH_RUNTIME_OBSERVATION_V1_OK" /tmp/equity_after_patch_runtime_observation_v1.log
grep -q "EQUITY_AFTER_PATCH_RUNTIME_OBSERVATION_SUMMARY" /tmp/equity_after_patch_runtime_observation_v1.log
grep -q "runtime_ok=" /tmp/equity_after_patch_runtime_observation_v1.log
grep -q "fresh_bars_total=" /tmp/equity_after_patch_runtime_observation_v1.log
grep -q "fresh_guard_rows=" /tmp/equity_after_patch_runtime_observation_v1.log
grep -q "VERDICT=" /tmp/equity_after_patch_runtime_observation_v1.log
grep -q "db_update=0" /tmp/equity_after_patch_runtime_observation_v1.log

echo
echo "=== EQUITY AFTER PATCH RUNTIME OBSERVATION SUMMARY ==="
grep -E "EQUITY_AFTER_PATCH_RUNTIME_ROW|EQUITY_AFTER_PATCH_BAR_ROW|EQUITY_AFTER_PATCH_GUARD_GROUP_ROW|EQUITY_AFTER_PATCH_SIGNAL_ROW|runtime_ok=|fresh_bars_total=|fresh_guard_rows=|fresh_signals=|equity_volatility_reason_rows=|br_volatility_reason_rows=|VERDICT=" \
  /tmp/equity_after_patch_runtime_observation_v1.log | head -180

echo TEST_EQUITY_AFTER_PATCH_RUNTIME_OBSERVATION_V1_OK
