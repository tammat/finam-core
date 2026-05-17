#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/alter_market_opportunity_scoring_v2.sql >/dev/null

python -m py_compile src/scripts/update_market_opportunity_scores_v2.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_market_opportunity_scores_v2.py").read_text(encoding="utf-8")

checks = [
    "trade_priority_score",
    "volatility_score",
    "rvol_score",
    "trend_efficiency_score",
    "event_risk_penalty",
    "churn_penalty",
    "ТОП-приоритет",
    "Торговый кандидат",
]

for c in checks:
    assert c in text, c

print("OK: market opportunity scoring v2 static check")
PY

PYTHONPATH=src python src/scripts/update_market_opportunity_scores_v2.py

psql "$DATABASE_URL" -P pager=off -c "
select
    symbol,
    trade_priority_score,
    trade_priority_label,
    trade_priority_reason
from market_opportunity_metrics
where trade_priority_score is not null
order by trade_priority_score desc
limit 20;
"

echo "OK: market opportunity scoring v2"
