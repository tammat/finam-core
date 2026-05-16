#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/backfill_smart_money_continuous.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/backfill_smart_money_continuous.py").read_text(encoding="utf-8")

assert "BR_CONT" in text
assert "BRM6@RTSX" in text
assert "smart_money_feature_events" in text
assert "backfill_smart_money_continuous" in text

print("OK: smart money continuous backfill static check")
PY
