#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_closed_trade_report.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/run_closed_trade_report.py").read_text(encoding="utf-8")

assert "COALESCE(t.origin, '') != 'backfill_from_fills'" in text
assert "ORDER BY t.symbol, t.ts, t.id" in text
assert text.index("COALESCE(t.origin, '') != 'backfill_from_fills'") < text.index("ORDER BY t.symbol, t.ts, t.id")

print("OK: closed trade report excludes backfill_from_fills")
PY
