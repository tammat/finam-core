#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/finam_core/research/unified_research_telemetry.py

OUT="$(python -m finam_core.research.unified_research_telemetry --demo)"

echo "$OUT" | grep -q "FINAM_CORE — ЕДИНАЯ RESEARCH-ТЕЛЕМЕТРИЯ"
echo "$OUT" | grep -q "Источник данных"
echo "$OUT" | grep -q "br_conservative_breakout"
echo "$OUT" | grep -q "BRN6@RTSX"
echo "$OUT" | grep -q "PROMOTION_CANDIDATE"

echo "UNIFIED_RESEARCH_TELEMETRY_V1_TEST_OK"
