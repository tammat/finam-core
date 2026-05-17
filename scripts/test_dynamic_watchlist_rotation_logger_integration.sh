#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_runtime_universe_rotation_log.sql >/dev/null

python -m py_compile \
  src/scripts/update_dynamic_watchlist_from_opportunities.py \
  src/finam_core/runtime/runtime_universe_rotation_logger.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_dynamic_watchlist_from_opportunities.py").read_text(encoding="utf-8")

checks = [
    "RuntimeUniverseRotationLogger",
    "rotation_logger.log_rotation",
    "classify_rotation_action",
    "FRESHNESS_EXPIRED",
    "SCORE_DROP",
    "DOWNGRADE",
    "previous_by_symbol",
    "freshness_score_value",
]

for c in checks:
    assert c in text, c

print("OK: dynamic watchlist rotation logger integration static check")
PY

PYTHONPATH=src python src/scripts/update_dynamic_watchlist_from_opportunities.py

psql "$DATABASE_URL" -P pager=off -c "
select symbol, action, previous_status, new_status, score, freshness_adjusted_score, reason
from runtime_universe_rotation_log
order by created_at desc
limit 20;
"

echo "OK: dynamic watchlist rotation logger integration"
