#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_trusted_strategy_statistics_v1.py

grep -q "RESEARCH_DATA_QUALITY_GATE_V1_WIRE" \
  src/scripts/research/build_trusted_strategy_statistics_v1.py

python3 src/scripts/research/build_research_data_quality_gate_v1.py \
  | tee /tmp/research_dq_gate_before_trusted_v1.log

python3 src/scripts/research/build_trusted_strategy_statistics_v1.py \
  | tee /tmp/wire_research_dq_gate_to_trusted_statistics_v1.log

grep -q "TRUSTED_STRATEGY_STATISTICS_V1_OK" \
  /tmp/wire_research_dq_gate_to_trusted_statistics_v1.log

psql "$DATABASE_URL" -c "
select
    trusted_status,
    trusted_reason,
    count(*) rows
from trusted_strategy_statistics_v1
group by trusted_status, trusted_reason
order by rows desc;
"

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trusted_strategy_statistics_v1 t
left join research_data_quality_gate_v1 dq
  on dq.symbol=t.symbol
 and dq.strategy=t.strategy
 and dq.timeframe=t.timeframe
 and dq.trade_source=t.trade_source
where t.trusted_status='TRUSTED'
  and (
       dq.gate_status is distinct from 'OPEN'
    or coalesce(dq.allow_statistics,false)=false
  );
")

echo "unsafe_dq_blocked_trusted_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: DQ-blocked strategy became TRUSTED"
  exit 1
fi

echo TEST_WIRE_RESEARCH_DQ_GATE_TO_TRUSTED_STATISTICS_V1_OK
