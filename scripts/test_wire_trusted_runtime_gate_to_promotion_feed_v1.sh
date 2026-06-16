#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/build_strategy_promotion_feed.py

grep -q "TRUSTED_RUNTIME_GATE_V1_WIRE" \
  src/scripts/build_strategy_promotion_feed.py

python3 src/scripts/build_strategy_promotion_feed.py --migrate --save \
  | tee /tmp/wire_trusted_runtime_gate_to_promotion_feed_v1.log

grep -q "STRATEGY_PROMOTION_FEED_SUMMARY" \
  /tmp/wire_trusted_runtime_gate_to_promotion_feed_v1.log

psql "$DATABASE_URL" -c "
select
    runtime_action,
    allow_paper_signal,
    allow_radar_signal,
    allow_real_suggestion,
    count(*) rows
from strategy_promotion_runtime_feed
group by
    runtime_action,
    allow_paper_signal,
    allow_radar_signal,
    allow_real_suggestion
order by rows desc;
"

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from strategy_promotion_runtime_feed
where coalesce(allow_paper_signal,false)=true
   or coalesce(allow_real_suggestion,false)=true;
")

echo "unsafe_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: trusted runtime gate did not fully close promotion feed"
  exit 1
fi

psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    runtime_action,
    allow_paper_signal,
    allow_radar_signal,
    allow_real_suggestion,
    reason
from strategy_promotion_runtime_feed
order by symbol,strategy,timeframe
limit 30;
"

echo TEST_WIRE_TRUSTED_RUNTIME_GATE_TO_PROMOTION_FEED_V1_OK
