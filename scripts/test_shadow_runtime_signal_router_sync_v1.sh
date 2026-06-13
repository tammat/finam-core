#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_shadow_runtime_signal_router_sync_v1.py

python3 src/scripts/runtime/build_shadow_runtime_signal_router_sync_v1.py \
  | tee /tmp/shadow_runtime_signal_router_sync_v1.log

grep -q "SHADOW RUNTIME SIGNAL ROUTER SYNC V1" /tmp/shadow_runtime_signal_router_sync_v1.log
grep -q "GDU6@RTSX" /tmp/shadow_runtime_signal_router_sync_v1.log
grep -q "LKOH@MISX" /tmp/shadow_runtime_signal_router_sync_v1.log
grep -q "runtime_shadow_gold_signals" /tmp/shadow_runtime_signal_router_sync_v1.log
grep -q "lkoh_shadow_signals" /tmp/shadow_runtime_signal_router_sync_v1.log
grep -q "SUMMARY_ROW planned=2 pending=0 skipped=3" /tmp/shadow_runtime_signal_router_sync_v1.log
grep -q "runtime_allow=0" /tmp/shadow_runtime_signal_router_sync_v1.log
grep -q "execution_enabled=0" /tmp/shadow_runtime_signal_router_sync_v1.log
grep -q "SHADOW_RUNTIME_SIGNAL_ROUTER_SYNC_V1_OK" /tmp/shadow_runtime_signal_router_sync_v1.log

echo TEST_SHADOW_RUNTIME_SIGNAL_ROUTER_SYNC_V1_OK
