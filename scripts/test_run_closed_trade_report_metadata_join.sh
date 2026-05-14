#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_closed_trade_report.py \
  src/finam_core/analytics/closed_trade_engine.py \
  src/finam_core/analytics/closed_trade_repository.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/run_closed_trade_report.py").read_text(encoding="utf-8")

assert "LEFT JOIN signal_fills sf" in text
assert "LEFT JOIN signals s" in text
assert "'signal_id', s.signal_id" in text
assert "'strategy', s.strategy" in text
assert "'horizon', s.horizon" in text
assert "'regime', s.regime" in text
assert "coalesce(t.payload, '{}'::jsonb)" in text

print("OK: run_closed_trade_report metadata join")
PY
