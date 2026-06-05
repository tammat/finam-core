#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/materialize_regime_guard_candidate_v1.py

python3 src/scripts/research/materialize_regime_guard_candidate_v1.py | \
  tee /tmp/regime_guard_candidate_v1.log

grep -q "MATERIALIZE REGIME GUARD CANDIDATE V1" /tmp/regime_guard_candidate_v1.log
grep -q "CANDIDATE_ROW" /tmp/regime_guard_candidate_v1.log
grep -q "ROWS_WRITTEN=" /tmp/regime_guard_candidate_v1.log
grep -q "VERDICT=OK" /tmp/regime_guard_candidate_v1.log

psql "$DATABASE_URL" -c "
select
  scope,
  classification,
  count(*) as rows
from research_regime_guard_candidates
where source='regime_guard_candidate_v1'
group by scope, classification
order by scope, classification;
"

psql "$DATABASE_URL" -c "
select
  scope,
  regime_key,
  classification,
  reason,
  trades,
  round(net_pnl::numeric, 6) as net_pnl,
  round(expectancy::numeric, 6) as expectancy,
  round(profit_factor::numeric, 6) as profit_factor
from research_regime_guard_candidates
where source='regime_guard_candidate_v1'
order by
  case classification
    when 'BLOCK_CANDIDATE' then 0
    when 'WATCH_CANDIDATE' then 1
    when 'ALLOW_CANDIDATE' then 2
    else 3
  end,
  net_pnl asc
limit 30;
"

echo REGIME_GUARD_CANDIDATE_V1_OK
