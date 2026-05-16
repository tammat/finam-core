#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/update_market_opportunity_metrics.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_market_opportunity_metrics.py").read_text(encoding="utf-8")

assert "insert into market_opportunity_metrics" in text
assert "from volatility_scan_results" in text
assert "raw_json->>'rvol'" in text
assert "raw_json->>'regime'" in text
assert "raw_json->>'spread_pct'" in text
assert "raw_json->>'range_pct'" in text
assert "symbol like '%@MISX'" in text

print("OK: market opportunity updater uses volatility_scan_results")
PY
