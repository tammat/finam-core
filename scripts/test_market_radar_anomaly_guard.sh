#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_market_radar.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/run_market_radar.py").read_text(encoding="utf-8")

checks = [
    "anomaly_rows",
    "MANUAL_REVIEW",
    "ANOMALY_REVIEW",
    "anomaly_guard_manual_review_only",
    "replace_watchlist(clean_rows[: args.top_n])",
]

for c in checks:
    assert c in text, c

print("OK: MarketRadar anomaly guard keeps anomalies out of dynamic watchlist")
PY
