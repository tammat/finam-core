#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MICRO_LIVE_GATE_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_micro_live_gate_audit_v1.py

src/scripts/research/build_micro_live_gate_audit_v1.py \
  | tee /tmp/micro_live_gate_audit_v1.out

grep -q "MICRO_LIVE_GATE_AUDIT_V1" /tmp/micro_live_gate_audit_v1.out
grep -q "real_trading_enabled=0" /tmp/micro_live_gate_audit_v1.out
grep -q "orders_sent=0" /tmp/micro_live_gate_audit_v1.out
grep -q "GATE code=EDGE_CANDIDATE_SELECTED status=BLOCKED" /tmp/micro_live_gate_audit_v1.out
grep -q "GATE code=KILL_SWITCH_VALIDATED status=BLOCKED" /tmp/micro_live_gate_audit_v1.out
grep -q "GATE code=REAL_EXECUTION_GUARD_VALIDATED status=BLOCKED" /tmp/micro_live_gate_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/micro_live_gate_audit_v1.out
grep -q "required=EDGE_CANDIDATE_SELECTION_FOR_MICRO_LIVE_V1" /tmp/micro_live_gate_audit_v1.out
grep -q "rule=no_micro_live_with_blocked_gate" /tmp/micro_live_gate_audit_v1.out
grep -q "VERDICT=MICRO_LIVE_GATE_AUDIT_BLOCKED_NOT_ENABLED" /tmp/micro_live_gate_audit_v1.out

echo "TEST_MICRO_LIVE_GATE_AUDIT_V1_OK"
