#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/trade_outcome_quality_engine.py \
  src/scripts/build_trade_outcome_quality.py

python src/scripts/build_trade_outcome_quality.py

psql "$DATABASE_URL" -c "
select
  quality_grade,
  count(*) rows,
  round(avg(quality_score)::numeric, 2) avg_score
from trade_outcome_quality_v1
group by quality_grade
order by quality_grade;
"

echo "TRADE_OUTCOME_QUALITY_V1_COMPILE_OK"
