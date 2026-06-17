#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NGQ6 FORWARD PARTIAL EXIT TO V3 REBUILD V1 ==="
echo "mode=auto_rebuild_after_forward_exit"
echo "runtime_allow=0"
echo "execution_enabled=0"

echo
echo "=== 1. FORWARD TRADES BEFORE REBUILD ==="
psql "$DATABASE_URL" -c "
select
    id,
    created_at,
    side,
    strategy,
    timeframe,
    origin,
    trade_source,
    qty,
    price
from trades
where symbol='NGQ6@RTSX'
  and coalesce(trade_source,'')='paper'
  and coalesce(origin,'paper')='paper'
  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
  and timeframe='M1'
  and created_at >= now() - interval '24 hours'
order by created_at;
"

echo
echo "=== 2. CURRENT POSITION STATE ==="
psql "$DATABASE_URL" -c "
select
    count(*) filter (where side='BUY') as buys_24h,
    count(*) filter (where side='SELL') as sells_24h,
    coalesce(sum(
        case
            when side='BUY' then qty
            when side='SELL' then -qty
            else 0
        end
    ),0) as net_qty_24h
from trades
where symbol='NGQ6@RTSX'
  and coalesce(trade_source,'')='paper'
  and coalesce(origin,'paper')='paper'
  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
  and timeframe='M1'
  and created_at >= now() - interval '24 hours';
"

echo
echo "=== 3. REBUILD CLEAN V3 ==="
bash scripts/test_ng_multi_contract_forward_accumulation_v1.sh

echo
echo "=== 4. NGQ6 M1 CHAINS AFTER REBUILD ==="
psql "$DATABASE_URL" -c "
select
    id,
    entry_trade_id,
    exit_trade_id,
    entry_ts,
    exit_ts,
    side,
    entry_price,
    exit_price,
    round(net_pnl,6) as pnl,
    quality_status,
    quality_reason
from closed_trade_chains_v3
where symbol='NGQ6@RTSX'
  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
  and timeframe='M1'
  and trade_source='paper'
order by exit_ts desc, id desc
limit 10;
"

echo
echo "=== 5. NGQ6 M1 TRACKER AFTER REBUILD ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    clean_trades,
    trade_days,
    v3_full_chains,
    v3_partial_chains,
    round(v3_net_pnl,6) as pnl,
    round(v3_net_pnl / nullif(v3_full_chains,0),6) as expectancy,
    accumulation_status,
    accumulation_reason
from clean_paper_accumulation_tracker_v1
where symbol='NGQ6@RTSX'
  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
  and timeframe='M1';
"

chains=$(psql "$DATABASE_URL" -At -c "
select coalesce(v3_full_chains,0)
from clean_paper_accumulation_tracker_v1
where symbol='NGQ6@RTSX'
  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
  and timeframe='M1';
")

recent_chain=$(psql "$DATABASE_URL" -At -c "
select count(*)
from closed_trade_chains_v3
where symbol='NGQ6@RTSX'
  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
  and timeframe='M1'
  and trade_source='paper'
  and entry_trade_id=30374
  and exit_trade_id=30379;
")

echo "ngq6_m1_v3_full_chains=${chains}"
echo "ngq6_forward_chain_30374_30379=${recent_chain}"

if [ "${chains}" -lt 11 ]; then
  echo "FAIL: expected NGQ6 M1 v3_full_chains >= 11 after forward exit"
  exit 1
fi

if [ "${recent_chain}" != "1" ]; then
  echo "FAIL: expected forward chain entry=30374 exit=30379"
  exit 1
fi

echo "NGQ6_FORWARD_PARTIAL_EXIT_TO_V3_REBUILD_V1_OK"
