#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_runtime_active_universe.sql >/dev/null

python -m py_compile \
  src/finam_core/runtime/runtime_universe_allocator.py \
  src/scripts/run_runtime_universe_allocator.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/runtime/runtime_universe_allocator.py").read_text(encoding="utf-8")

checks = [
    "RuntimeUniverseAllocator",
    "dynamic_watchlist",
    "runtime_active_universe",
    "not_selected_by_runtime_allocator",
    "max_symbols",
    "min_score",
]

for c in checks:
    assert c in text, c

print("OK: RuntimeUniverseAllocator static check")
PY

PYTHONPATH=src python src/scripts/run_runtime_universe_allocator.py

psql "$DATABASE_URL" -P pager=off -c "
select symbol, strategy, regime, score, priority, is_enabled, disable_reason
from runtime_active_universe
order by is_enabled desc, score desc;
"

echo "OK: RuntimeUniverseAllocator"
