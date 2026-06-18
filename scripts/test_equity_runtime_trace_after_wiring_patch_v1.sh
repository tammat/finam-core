#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY RUNTIME TRACE AFTER WIRING PATCH V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py
python3 -m py_compile src/scripts/runtime/build_equity_intent_generation_trace_v1.py
python3 -m py_compile src/scripts/runtime/build_equity_strategy_intent_flow_diagnostic_v1.py

grep -q "EQUITY_STRATEGY_WIRING_PATCH_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "def _runtime_strategy_name_for_symbol" src/finam_core/pipelines/paper_pipeline.py

echo
echo "=== CURRENT TRACE BEFORE/AFTER SERVICE RESTART ==="

EQUITY_TRACE_SYMBOL="${EQUITY_TRACE_SYMBOL:-SBER@MISX}" \
EQUITY_TRACE_STRATEGY="${EQUITY_TRACE_STRATEGY:-VOLATILITY_BREAKOUT_EQUITY}" \
PYTHONPATH=src python3 src/scripts/runtime/build_equity_intent_generation_trace_v1.py \
  | tee /tmp/equity_runtime_trace_after_wiring_patch_v1.log

grep -q "EQUITY_INTENT_GENERATION_TRACE_V1_OK" /tmp/equity_runtime_trace_after_wiring_patch_v1.log
grep -q "expected_strategy=VOLATILITY_BREAKOUT_EQUITY" /tmp/equity_runtime_trace_after_wiring_patch_v1.log
grep -q "db_update=0" /tmp/equity_runtime_trace_after_wiring_patch_v1.log
grep -q "VERDICT=" /tmp/equity_runtime_trace_after_wiring_patch_v1.log

echo
echo "=== EQUITY RUNTIME TRACE AFTER WIRING PATCH SUMMARY ==="
grep -E "signals_count=|signal_features_count=|runtime_guard_count=|expected_strategy=|expected_strategy_guard_count=|other_strategy_guard_count=|execution_intents_count=|position_intents_count=|diagnosis=|next_step=|VERDICT=" \
  /tmp/equity_runtime_trace_after_wiring_patch_v1.log

echo TEST_EQUITY_RUNTIME_TRACE_AFTER_WIRING_PATCH_V1_OK
