#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST NGQ6 FORWARD EXIT MONITOR V1 ==="

python3 -m py_compile src/scripts/research/build_ngq6_forward_exit_monitor_v1.py

python3 src/scripts/research/build_ngq6_forward_exit_monitor_v1.py \
  | tee /tmp/ngq6_forward_exit_monitor_v1.log

grep -q "NGQ6_FORWARD_EXIT_MONITOR_V1_OK" /tmp/ngq6_forward_exit_monitor_v1.log
grep -q "VERDICT=" /tmp/ngq6_forward_exit_monitor_v1.log
grep -q "runtime_allow=0" /tmp/ngq6_forward_exit_monitor_v1.log
grep -q "execution_enabled=0" /tmp/ngq6_forward_exit_monitor_v1.log
grep -q "bad_identity_rows=0" /tmp/ngq6_forward_exit_monitor_v1.log

echo TEST_NGQ6_FORWARD_EXIT_MONITOR_V1_OK
