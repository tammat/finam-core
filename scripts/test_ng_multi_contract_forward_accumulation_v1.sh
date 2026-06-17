#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NG MULTI CONTRACT FORWARD ACCUMULATION V1 ==="
echo "mode=auto_rebuild"
echo "runtime_allow=0"
echo "execution_enabled=0"

echo
echo "=== 1. SOURCE TRADES ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    count(*) trades,
    min(created_at) first_trade,
    max(created_at) last_trade
from trades
where symbol in ('NGM6@RTSX','NGQ6@RTSX')
  and strategy in ('NG_CONSERVATIVE_BREAKOUT','NG_CONSERVATIVE_BREAKOUT_M1')
group by 1,2,3
order by symbol, strategy, timeframe;
"

echo
echo "=== 2. REBUILD V3 ==="
bash scripts/test_fill_pairing_engine_v3_skip_burst.sh
bash scripts/test_trade_attribution_v3_from_chains_v3.sh
bash scripts/test_strategy_statistics_v3_from_attribution_v3.sh
bash scripts/test_clean_paper_accumulation_tracker_v1.sh

echo
echo "=== 3. NG MULTI CONTRACT CLEAN V3 ==="
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
    accumulation_reason
from clean_paper_accumulation_tracker_v1
where symbol in ('NGM6@RTSX','NGQ6@RTSX')
  and strategy in ('NG_CONSERVATIVE_BREAKOUT','NG_CONSERVATIVE_BREAKOUT_M1')
order by expectancy desc;
"

echo
echo "=== 4. EDGE COMPARISON ==="
bash scripts/test_ng_multi_contract_edge_comparison_v1.sh

echo "NG_MULTI_CONTRACT_FORWARD_ACCUMULATION_V1_OK"
