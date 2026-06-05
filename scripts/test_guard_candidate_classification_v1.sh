#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/materialize_guard_candidate_classification_v1.py

python3 src/scripts/analytics/materialize_guard_candidate_classification_v1.py | tee /tmp/guard_candidate_classification_v1.log

grep -q "VERDICT=OK" /tmp/guard_candidate_classification_v1.log
grep -q "ROWS_WRITTEN=" /tmp/guard_candidate_classification_v1.log
grep -q "CLASS_ROW" /tmp/guard_candidate_classification_v1.log

psql "$DATABASE_URL" -c "
select
  classification,
  count(*) as rows
from guard_candidate_classification_state
where source='guard_candidate_classification_v1'
group by classification
order by classification;
"

psql "$DATABASE_URL" -c "
select
  symbol,
  strategy,
  timeframe,
  side,
  session_bucket,
  classification,
  reason,
  total_trades,
  total_net_pnl,
  expectancy,
  stop_rate,
  take_rate,
  pf_proxy
from guard_candidate_classification_state
where source='guard_candidate_classification_v1'
order by
  case classification
    when 'BLOCK_READY' then 0
    when 'RESEARCH_ONLY' then 1
    when 'KEEP_WATCH' then 2
    else 3
  end,
  total_net_pnl asc;
"
echo GUARD_CANDIDATE_CLASSIFICATION_V1_OK
