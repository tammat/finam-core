#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NG MULTI CONTRACT EDGE COMPARISON V1 ==="
echo "mode=diagnostic"
echo "runtime_allow=0"
echo "execution_enabled=0"

psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    clean_trades,
    trade_days,
    v3_full_chains,
    round(v3_net_pnl,6) as pnl,
    round(v3_net_pnl / nullif(v3_full_chains,0),6) as expectancy,
    accumulation_status,
    accumulation_reason,
    case
        when v3_full_chains < 50 or trade_days < 5 then 'LOW_SAMPLE'
        when v3_net_pnl > 0 then 'WATCH_CANDIDATE'
        else 'REJECT_CANDIDATE'
    end as edge_verdict
from clean_paper_accumulation_tracker_v1
where symbol in ('NGM6@RTSX','NGQ6@RTSX')
  and strategy in ('NG_CONSERVATIVE_BREAKOUT','NG_CONSERVATIVE_BREAKOUT_M1')
order by
    edge_verdict desc,
    expectancy desc,
    symbol,
    timeframe;
"

echo
echo "=== NG BEST CURRENT CANDIDATE ==="

psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    v3_full_chains,
    trade_days,
    round(v3_net_pnl,6) as pnl,
    round(v3_net_pnl / nullif(v3_full_chains,0),6) as expectancy
from clean_paper_accumulation_tracker_v1
where symbol in ('NGM6@RTSX','NGQ6@RTSX')
  and strategy in ('NG_CONSERVATIVE_BREAKOUT','NG_CONSERVATIVE_BREAKOUT_M1')
order by expectancy desc
limit 1;
"

echo "NG_MULTI_CONTRACT_EDGE_COMPARISON_V1_OK"
