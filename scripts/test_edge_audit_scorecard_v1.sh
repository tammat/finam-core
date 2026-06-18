#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EDGE AUDIT SCORECARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_edge_audit_scorecard_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_edge_audit_scorecard_v1.py \
  | tee /tmp/edge_audit_scorecard_v1.log

grep -q "EDGE_AUDIT_SCORECARD_V1_OK" /tmp/edge_audit_scorecard_v1.log
grep -q "EDGE_AUDIT_SUMMARY" /tmp/edge_audit_scorecard_v1.log
grep -q "gross_pnl_total=" /tmp/edge_audit_scorecard_v1.log
grep -q "commission_total=" /tmp/edge_audit_scorecard_v1.log
grep -q "net_pnl_total=" /tmp/edge_audit_scorecard_v1.log
grep -q "VERDICT=" /tmp/edge_audit_scorecard_v1.log
grep -q "db_update=0" /tmp/edge_audit_scorecard_v1.log

echo
echo "=== EDGE AUDIT SCORECARD SUMMARY ==="
grep -E "EDGE_AUDIT_ROW|gross_pnl_total=|commission_total=|net_pnl_total=|fee_drag_rows=|negative_edge_rows=|research_candidates=|VERDICT=" \
  /tmp/edge_audit_scorecard_v1.log

echo TEST_EDGE_AUDIT_SCORECARD_V1_OK
