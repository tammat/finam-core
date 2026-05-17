#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/runtime_rebalance_loop.py \
  src/scripts/run_runtime_universe_allocator.py \
  src/finam_core/runtime/runtime_universe_allocator.py

python - <<'PY'
from pathlib import Path

loop = Path("src/scripts/runtime_rebalance_loop.py").read_text(encoding="utf-8")
allocator = Path("src/finam_core/runtime/runtime_universe_allocator.py").read_text(encoding="utf-8")

assert "update_dynamic_watchlist_from_opportunities.py" in loop
assert "run_runtime_universe_allocator.py" in loop
assert loop.find("update_dynamic_watchlist_from_opportunities.py") < loop.find("run_runtime_universe_allocator.py")
assert "freshness_adjusted_scoring_v2" in allocator

print("OK: runtime rebalance runs allocator after dynamic watchlist")
PY

PYTHONPATH=src python src/scripts/run_runtime_universe_allocator.py
