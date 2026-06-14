#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_shadow_runtime_pnl_monitor_v1.py

python3 src/scripts/runtime/build_shadow_runtime_pnl_monitor_v1.py \
  | tee /tmp/shadow_runtime_pnl_monitor_v1.log

grep -q "SHADOW RUNTIME PNL MONITOR V1" /tmp/shadow_runtime_pnl_monitor_v1.log
grep -q "PNL_ROW" /tmp/shadow_runtime_pnl_monitor_v1.log
grep -q "LKOH@MISX" /tmp/shadow_runtime_pnl_monitor_v1.log
grep -q "RECONCILED" /tmp/shadow_runtime_pnl_monitor_v1.log
grep -q "runtime_allow=0" /tmp/shadow_runtime_pnl_monitor_v1.log
grep -q "execution_enabled=0" /tmp/shadow_runtime_pnl_monitor_v1.log
grep -q "SHADOW_RUNTIME_PNL_MONITOR_V1_OK" /tmp/shadow_runtime_pnl_monitor_v1.log

echo TEST_SHADOW_RUNTIME_PNL_MONITOR_V1_OK
