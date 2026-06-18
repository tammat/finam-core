#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY INTENT GENERATION TRACE V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_intent_generation_trace_v1.py

EQUITY_TRACE_SYMBOL="${EQUITY_TRACE_SYMBOL:-SBER@MISX}" \
PYTHONPATH=src python3 src/scripts/runtime/build_equity_intent_generation_trace_v1.py \
  | tee /tmp/equity_intent_generation_trace_v1.log

grep -q "EQUITY_INTENT_GENERATION_TRACE_V1_OK" /tmp/equity_intent_generation_trace_v1.log
grep -q "EQUITY_TRACE_TABLES" /tmp/equity_intent_generation_trace_v1.log
grep -q "EQUITY_TRACE_SECTION_SUMMARY" /tmp/equity_intent_generation_trace_v1.log
grep -q "EQUITY_INTENT_GENERATION_TRACE_SUMMARY" /tmp/equity_intent_generation_trace_v1.log
grep -q "db_update=0" /tmp/equity_intent_generation_trace_v1.log
grep -q "VERDICT=" /tmp/equity_intent_generation_trace_v1.log

echo
echo "=== EQUITY INTENT GENERATION TRACE SUMMARY ==="
grep -E "EQUITY_TRACE_SECTION|signals_count=|signal_features_count=|signal_quality_count=|runtime_guard_count=|execution_intents_count=|position_intents_count=|execution_events_count=|risk_events_count=|diagnosis=|next_step=|VERDICT=" \
  /tmp/equity_intent_generation_trace_v1.log

echo TEST_EQUITY_INTENT_GENERATION_TRACE_V1_OK
