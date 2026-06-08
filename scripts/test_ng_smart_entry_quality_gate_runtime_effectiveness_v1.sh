#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_ng_smart_entry_quality_gate_runtime_effectiveness_v1.py

python3 src/scripts/analytics/build_ng_smart_entry_quality_gate_runtime_effectiveness_v1.py | tee /tmp/ng_smart_entry_quality_gate_runtime_effectiveness_v1.log

grep -q "NG SMART ENTRY QUALITY GATE RUNTIME EFFECTIVENESS V1" /tmp/ng_smart_entry_quality_gate_runtime_effectiveness_v1.log
grep -q "GATE_RUNTIME_SUMMARY" /tmp/ng_smart_entry_quality_gate_runtime_effectiveness_v1.log
grep -q "NG_TRADES_AFTER_GATE" /tmp/ng_smart_entry_quality_gate_runtime_effectiveness_v1.log
grep -q "NG_CLOSED_AFTER_GATE" /tmp/ng_smart_entry_quality_gate_runtime_effectiveness_v1.log
grep -q "NG_SMART_ENTRY_QUALITY_GATE_RUNTIME_EFFECTIVENESS_V1_OK" /tmp/ng_smart_entry_quality_gate_runtime_effectiveness_v1.log

echo "TEST_NG_SMART_ENTRY_QUALITY_GATE_RUNTIME_EFFECTIVENESS_V1_OK"
