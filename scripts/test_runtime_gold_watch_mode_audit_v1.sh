#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_runtime_gold_watch_mode_audit_v1.py

python3 src/scripts/runtime/build_runtime_gold_watch_mode_audit_v1.py \
  | tee /tmp/runtime_gold_watch_mode_audit_v1.log

grep -q "RUNTIME GOLD WATCH MODE AUDIT V1" /tmp/runtime_gold_watch_mode_audit_v1.log
grep -q "status=WATCH_RUNTIME_ACTIVE" /tmp/runtime_gold_watch_mode_audit_v1.log
grep -q "runtime_allowed=0" /tmp/runtime_gold_watch_mode_audit_v1.log
grep -q "execution_enabled=0" /tmp/runtime_gold_watch_mode_audit_v1.log
grep -q "orders_ok=1" /tmp/runtime_gold_watch_mode_audit_v1.log
grep -q "fills_ok=1" /tmp/runtime_gold_watch_mode_audit_v1.log
grep -q "positions_ok=1" /tmp/runtime_gold_watch_mode_audit_v1.log
grep -q "AUDIT_VERDICT=PASS" /tmp/runtime_gold_watch_mode_audit_v1.log
grep -q "RUNTIME_GOLD_WATCH_MODE_AUDIT_V1_OK" /tmp/runtime_gold_watch_mode_audit_v1.log

echo TEST_RUNTIME_GOLD_WATCH_MODE_AUDIT_V1_OK
