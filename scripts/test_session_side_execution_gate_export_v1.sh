#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_SESSION_SIDE_EXECUTION_GATE_EXPORT_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_session_side_execution_gate_export_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "SESSION_SIDE_EXECUTION_GATE_EXPORT_V1" "$TMP_LOG"
grep -q "SESSION_SIDE_EXECUTION_GATE_EXPORT_STATUS" "$TMP_LOG"
grep -q "SESSION_SIDE_EXECUTION_GATE_EXPORT_V1_OK" "$TMP_LOG"

test -f runtime/session_side_execution_gate_v1.json

python - <<'PY'
import json
from pathlib import Path

p = Path("runtime/session_side_execution_gate_v1.json")
data = json.loads(p.read_text(encoding="utf-8"))

assert "allow" in data
assert "block" in data
assert "insufficient_data" in data
assert data["version"] == "session_side_execution_gate_v1"

print("SESSION_SIDE_EXECUTION_GATE_EXPORT_JSON_OK")
PY

echo "TEST_SESSION_SIDE_EXECUTION_GATE_EXPORT_V1_OK"
