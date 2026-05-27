#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/finam_core/research/unified_research_telemetry.py

OUT="$(python -m finam_core.research.unified_research_telemetry --demo)"

echo "$OUT" | grep -q "FINAM_CORE — ЕДИНАЯ RESEARCH-ТЕЛЕМЕТРИЯ"
echo "$OUT" | grep -q "Production health"
echo "$OUT" | grep -q "Research supervisor"
echo "$OUT" | grep -q "RESEARCH_SUPERVISOR_FAILED"
echo "$OUT" | grep -q "BR_CONSERVATIVE_BREAKOUT"

echo "UNIFIED_RESEARCH_TELEMETRY_V2_TEST_OK"
