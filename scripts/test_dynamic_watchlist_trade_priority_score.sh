#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/update_dynamic_watchlist_from_opportunities.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_dynamic_watchlist_from_opportunities.py").read_text(encoding="utf-8")

checks = [
    "trade_priority_score",
    "trade_priority_label",
    "trade_priority_reason",
    "event_risk_penalty",
    "churn_penalty",
    "trade_priority_scoring_v2",
    "MIN_TRADE_PRIORITY_SCORE",
]

for c in checks:
    assert c in text, c

assert "PostgresOpportunityScanner" not in text
assert "x.opportunity_score" not in text

print("OK: dynamic watchlist uses trade_priority_score")
PY

PYTHONPATH=src python src/scripts/update_dynamic_watchlist_from_opportunities.py

psql "$DATABASE_URL" -P pager=off -c "
select
    symbol,
    score,
    strategy,
    regime,
    priority,
    source,
    reason
from dynamic_watchlist
where source = 'trade_priority_scoring_v2'
order by score desc
limit 20;
"

echo "OK: dynamic watchlist trade priority score"
