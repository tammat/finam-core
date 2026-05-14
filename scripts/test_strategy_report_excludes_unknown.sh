#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/strategy_performance_report.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/strategy_performance_report.py").read_text(encoding="utf-8")

assert "UNATTRIBUTED_CLOSED_TRADES" in text
assert "not in ('', 'UNKNOWN')" in text
assert "coalesce(signal_id, payload->'entry_payload'->>'signal_id', '') <> ''" in text
assert "CLEAN_CLOSED_TRADES_PERFORMANCE" in text

print("OK: strategy report separates UNKNOWN from clean analytics")
PY
