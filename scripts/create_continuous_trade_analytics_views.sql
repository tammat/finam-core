create or replace view analytics_trades_continuous as
select
    id,
    ts,
    symbol as execution_symbol,
    coalesce(payload->>'continuous_symbol', symbol) as analytics_symbol,
    payload->>'root_symbol' as root_symbol,
    payload->>'strategy' as strategy,
    payload->>'source' as source,
    payload->>'horizon' as horizon,
    payload->>'timeframe' as timeframe,
    payload->>'futures_month_code' as futures_month_code,
    payload->>'futures_year_code' as futures_year_code,
    payload->>'venue' as venue,
    payload->>'is_futures' as is_futures,
    side,
    qty,
    price,
    commission,
    origin,
    trade_source,
    payload
from trades;

create or replace view analytics_strategy_expectancy_continuous as
select
    analytics_symbol,
    strategy,
    count(*) as trades,
    min(ts) as first_trade_ts,
    max(ts) as last_trade_ts,
    round(sum(
        case
            when side = 'SELL' then price * qty
            when side = 'BUY' then -price * qty
            else 0
        end
    )::numeric, 4) as raw_cashflow
from analytics_trades_continuous
where strategy is not null
  and strategy <> ''
group by analytics_symbol, strategy;
