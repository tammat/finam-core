#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_trusted_strategy_statistics_v1.py

grep -q "QUARANTINE_RECONSTRUCTION_ARTIFACTS_V1_WIRE" \
  src/scripts/research/build_trusted_strategy_statistics_v1.py

python3 src/scripts/research/build_trusted_strategy_statistics_v1.py \
  | tee /tmp/wire_quarantine_to_trusted_statistics_v1.log

grep -q "TRUSTED_STRATEGY_STATISTICS_V1_OK" \
  /tmp/wire_quarantine_to_trusted_statistics_v1.log

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
join quarantine_reconstruction_artifacts_v1 q
  on q.symbol=t.symbol
 and q.strategy=t.strategy
 and q.timeframe=t.timeframe
 and q.trade_source=t.trade_source
where q.quarantine_status='QUARANTINED'
  and t.trusted_status='TRUSTED';
")

echo "unsafe_quarantined_trusted_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: quarantined strategy became TRUSTED"
  exit 1
fi

echo TEST_WIRE_QUARANTINE_TO_TRUSTED_STATISTICS_V1_OK
