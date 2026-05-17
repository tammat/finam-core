#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/alter_market_opportunity_freshness_score.sql >/dev/null

python -m py_compile src/scripts/update_market_opportunity_scores_v2.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_market_opportunity_scores_v2.py").read_text(encoding="utf-8")

checks = [
    "signal_age_min",
    "freshness_score",
    "freshness_adjusted_score",
    "freshness_reason",
    "age_min=",
]

for c in checks:
    assert c in text, c

print("OK: market opportunity freshness scoring static check")
PY

PYTHONPATH=src python src/scripts/update_market_opportunity_scores_v2.py

psql "$DATABASE_URL" -P pager=off -c "
select
    symbol,
    trade_priority_score,
    signal_age_min,
    freshness_score,
    freshness_adjusted_score,
    freshness_reason
from market_opportunity_metrics
where freshness_adjusted_score is not null
order by freshness_adjusted_score desc
limit 20;
"

echo "OK: market opportunity freshness score"
