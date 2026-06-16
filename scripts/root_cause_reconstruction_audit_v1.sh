#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== ROOT CAUSE RECONSTRUCTION AUDIT V1 ==="
echo "mode=research_only"
echo "runtime_allow=0"
echo "execution_enabled=0"

echo
echo "STEP_1_ATTRIBUTION_CHAIN_COUNTS"
psql "$DATABASE_URL" -c "
select
    a.symbol,
    a.strategy,
    a.timeframe,
    count(*) as attribution_rows,
    count(distinct a.closed_trade_id) as distinct_chains,
    count(distinct c.entry_ts::date) as entry_days,
    count(distinct c.exit_ts::date) as exit_days,
    min(c.entry_ts) as first_entry,
    max(c.exit_ts) as last_exit,
    sum(a.pnl) as pnl
from trade_attribution_v2 a
join closed_trade_chains_v2 c
  on c.id=a.closed_trade_id
where (a.symbol,a.strategy,a.timeframe) in (
    ('SBER@MISX','MOEX_SIMPLE_MOMENTUM','D1'),
    ('PLZL@MISX','MOEX_SIMPLE_MOMENTUM','D1'),
    ('PLZL@MISX','MOEX_MEAN_REVERSION_V1','D1'),
    ('BRN6@RTSX','BR_CONSERVATIVE_BREAKOUT','M5'),
    ('BRM6@RTSX','BR_CONSERVATIVE_BREAKOUT','M5'),
    ('NGN6@RTSX','NG_CONSERVATIVE_BREAKOUT','M5'),
    ('NGM6@RTSX','NG_CONSERVATIVE_BREAKOUT','M5'),
    ('LKOH@MISX','MOEX_SIMPLE_MOMENTUM','D1')
)
group by a.symbol,a.strategy,a.timeframe
order by attribution_rows desc;
"

echo
echo "STEP_2_ORIGIN_DISTRIBUTION"
psql "$DATABASE_URL" -c "
select
    a.symbol,
    a.strategy,
    a.timeframe,
    t.origin,
    t.trade_source,
    count(*) as fills
from trade_attribution_v2 a
join closed_trade_chains_v2 c
  on c.id=a.closed_trade_id
join trades t
  on t.symbol=a.symbol
 and t.created_at between c.entry_ts and c.exit_ts
where (a.symbol,a.strategy,a.timeframe) in (
    ('SBER@MISX','MOEX_SIMPLE_MOMENTUM','D1'),
    ('PLZL@MISX','MOEX_SIMPLE_MOMENTUM','D1'),
    ('PLZL@MISX','MOEX_MEAN_REVERSION_V1','D1')
)
group by a.symbol,a.strategy,a.timeframe,t.origin,t.trade_source
order by a.symbol,a.strategy,fills desc;
"

echo
echo "STEP_3_DAY_CONCENTRATION"
psql "$DATABASE_URL" -c "
select
    a.symbol,
    a.strategy,
    a.timeframe,
    c.exit_ts::date as exit_day,
    count(*) as chains,
    sum(a.pnl) as pnl
from trade_attribution_v2 a
join closed_trade_chains_v2 c
  on c.id=a.closed_trade_id
where (a.symbol,a.strategy,a.timeframe) in (
    ('SBER@MISX','MOEX_SIMPLE_MOMENTUM','D1'),
    ('PLZL@MISX','MOEX_SIMPLE_MOMENTUM','D1'),
    ('PLZL@MISX','MOEX_MEAN_REVERSION_V1','D1')
)
group by a.symbol,a.strategy,a.timeframe,c.exit_ts::date
order by chains desc;
"

echo
echo "STEP_4_ATTRIBUTION_DUPLICATES"
psql "$DATABASE_URL" -c "
select
    closed_trade_id,
    symbol,
    strategy,
    timeframe,
    count(*) as attribution_rows,
    sum(pnl) as pnl
from trade_attribution_v2
group by closed_trade_id,symbol,strategy,timeframe
having count(*) > 1
order by attribution_rows desc
limit 30;
"

echo
echo "STEP_5_SAME_TIMESTAMP_FILL_BURSTS"
psql "$DATABASE_URL" -c "
select
    symbol,
    side,
    qty,
    price,
    created_at,
    count(*) as rows,
    min(id) as min_id,
    max(id) as max_id
from trades
where symbol in ('SBER@MISX','PLZL@MISX','BRN6@RTSX','BRM6@RTSX','NGN6@RTSX','NGM6@RTSX','LKOH@MISX')
group by symbol,side,qty,price,created_at
having count(*) >= 10
order by rows desc
limit 30;
"

echo
echo "STEP_6_INVALID_AND_BACKFILL_SUMMARY"
psql "$DATABASE_URL" -c "
select
    symbol,
    origin,
    trade_source,
    strategy,
    timeframe,
    is_invalid,
    invalid_reason,
    count(*) as rows
from trades
where symbol in ('SBER@MISX','PLZL@MISX','BRN6@RTSX','BRM6@RTSX','NGN6@RTSX','NGM6@RTSX','LKOH@MISX','USDRUBF@RTSX')
group by symbol,origin,trade_source,strategy,timeframe,is_invalid,invalid_reason
order by symbol,rows desc;
"

echo
echo "STEP_7_ROOT_CAUSE_VERDICT"
psql "$DATABASE_URL" -c "
with suspects as (
    select
        a.symbol,
        a.strategy,
        a.timeframe,
        count(*) as trades,
        count(distinct c.entry_ts::date) as entry_days,
        count(distinct c.exit_ts::date) as exit_days,
        count(*) filter (where a.attribution_quality='FULL') as full_ctx,
        count(*) filter (where a.attribution_quality='PARTIAL') as partial_ctx
    from trade_attribution_v2 a
    join closed_trade_chains_v2 c
      on c.id=a.closed_trade_id
    group by a.symbol,a.strategy,a.timeframe
)
select
    symbol,
    strategy,
    timeframe,
    trades,
    entry_days,
    exit_days,
    full_ctx,
    partial_ctx,
    case
        when trades >= 100 and (entry_days < 10 or exit_days < 10) and full_ctx = 0
            then 'ROOT_CAUSE_RECONSTRUCTION_OR_BACKFILL_ARTIFACT'
        when trades >= 100 and (entry_days < 10 or exit_days < 10)
            then 'ROOT_CAUSE_TIME_CONCENTRATION'
        else 'ROOT_CAUSE_NOT_CONFIRMED'
    end as root_cause_verdict
from suspects
where trades >= 100
order by
    case
        when trades >= 100 and (entry_days < 10 or exit_days < 10) then 0
        else 1
    end,
    trades desc;
"

echo
echo "ROOT_CAUSE_RECONSTRUCTION_AUDIT_V1_OK"
