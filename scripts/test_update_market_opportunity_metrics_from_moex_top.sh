#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/update_market_opportunity_metrics_from_moex_top.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_market_opportunity_metrics_from_moex_top.py").read_text(encoding="utf-8")

checks = [
    "moex_top_universe",
    "market_opportunity_metrics",
    "MOEX_TOP_TO_OPPORTUNITY_LIMIT",
    "top_score",
    "NO_SMART_MONEY_DATA",
]

for c in checks:
    assert c in text, c

print("OK: moex top to opportunity metrics static check")
PY

PYTHONPATH=src python src/scripts/update_market_opportunity_metrics_from_moex_top.py

psql "$DATABASE_URL" -P pager=off -c "
select
    symbol,
    asset_class,
    atr_pct,
    rvol,
    turnover,
    regime,
    raw->>'source' as source,
    calculated_at
from market_opportunity_metrics
where raw->>'source' = 'moex_top_universe'
order by calculated_at desc
limit 20;
"

echo "OK: moex top to opportunity metrics"
