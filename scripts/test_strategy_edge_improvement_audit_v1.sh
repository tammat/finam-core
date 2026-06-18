#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST STRATEGY EDGE IMPROVEMENT AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_strategy_edge_improvement_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_strategy_edge_improvement_audit_v1.py \
  | tee /tmp/strategy_edge_improvement_audit_v1.log

grep -q "STRATEGY_EDGE_IMPROVEMENT_AUDIT_V1_OK" /tmp/strategy_edge_improvement_audit_v1.log
grep -q "STRATEGY_EDGE_IMPROVEMENT_AUDIT_SUMMARY" /tmp/strategy_edge_improvement_audit_v1.log
grep -q "STRATEGY_EDGE_IMPROVEMENT_RECOMMENDATIONS" /tmp/strategy_edge_improvement_audit_v1.log
grep -q "missing_expected_move_rows=" /tmp/strategy_edge_improvement_audit_v1.log
grep -q "missing_spread_rows=" /tmp/strategy_edge_improvement_audit_v1.log
grep -q "missing_mfe_mae_rows=" /tmp/strategy_edge_improvement_audit_v1.log
grep -q "VERDICT=" /tmp/strategy_edge_improvement_audit_v1.log
grep -q "db_update=0" /tmp/strategy_edge_improvement_audit_v1.log

if grep -Eq "SKIPPED:|FAILED:|InFailedSqlTransaction|GroupingError" /tmp/strategy_edge_improvement_audit_v1.log; then
  echo "FAIL: audit query failed"
  exit 1
fi

if grep -q "VERDICT=STRATEGY_EDGE_IMPROVEMENT_AUDIT_QUERY_FAILURE" /tmp/strategy_edge_improvement_audit_v1.log; then
  echo "FAIL: audit query failure verdict"
  exit 1
fi

echo
echo "=== STRATEGY EDGE IMPROVEMENT AUDIT SUMMARY ==="
grep -E "STRATEGY_EDGE_IMPROVEMENT_AUDIT_SUMMARY|runtime_enabled_rows=|trades_total=|signal_class_rows=|unknown_signal_class_rows=|missing_expected_move_rows=|missing_spread_rows=|missing_mfe_mae_rows=|RECOMMENDATION|VERDICT=" \
  /tmp/strategy_edge_improvement_audit_v1.log

echo TEST_STRATEGY_EDGE_IMPROVEMENT_AUDIT_V1_OK
