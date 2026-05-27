#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/edge_validation_engine.py \
  src/scripts/analytics/build_edge_validation_report.py

python - <<'PY'
from finam_core.analytics.edge_validation_engine import EdgeValidationEngine

engine = EdgeValidationEngine()

r1 = engine.validate("BRN6@RTSX", "BR", "M5", [])
assert r1.status == "NO_VALID_TRADES", r1

r2 = engine.validate("BRN6@RTSX", "BR", "M5", [1.0, -0.5])
assert r2.status == "LOW_SAMPLE", r2

r3 = engine.validate("BRN6@RTSX", "BR", "M5", [2.0, -1.0] * 20)
assert r3.status == "EDGE_OK", r3

r4 = engine.validate("BRN6@RTSX", "BR", "M5", [0.5, -1.0] * 20)
assert r4.status == "EDGE_WEAK", r4

print("EDGE_VALIDATION_ENGINE_UNIT_OK")
PY

echo "EDGE_VALIDATION_ENGINE_V1_TEST_OK"
