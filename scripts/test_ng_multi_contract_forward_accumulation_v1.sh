#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NG MULTI CONTRACT FORWARD ACCUMULATION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

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
group by 1,2,3
order by symbol, strategy;
"

echo
echo "=== LAST 20 TRADES ==="

psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    side,
    price,
    created_at
from trades
where symbol in ('NGM6@RTSX','NGQ6@RTSX')
order by created_at desc
limit 20;
"

echo "NG_MULTI_CONTRACT_FORWARD_ACCUMULATION_V1_OK"
