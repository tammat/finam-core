#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/runtime_rebalance_loop.py \
  src/scripts/update_market_opportunity_metrics.py \
  src/scripts/update_dynamic_watchlist_from_opportunities.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/runtime_rebalance_loop.py").read_text(encoding="utf-8")

assert "update_market_opportunity_metrics.py" in text
assert "update_dynamic_watchlist_from_opportunities.py" in text
assert "OK: runtime rebalance loop completed" in text
assert "PYTHONPATH" in text

print("OK: runtime rebalance loop static check")
PY
