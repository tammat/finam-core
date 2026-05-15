create or replace view analytics_trades_normalized as
select
    id,
    ts,
    ts at time zone 'Europe/Moscow' as ts_msk,

    symbol as execution_symbol,
    coalesce(payload->>'continuous_symbol', symbol) as analytics_symbol,
    payload->>'root_symbol' as root_symbol,
    payload->>'strategy' as strategy,
    payload->>'source' as source,
    payload->>'horizon' as horizon,
    payload->>'timeframe' as timeframe,
    payload->>'regime' as regime,

    side,
    qty,
    price,
    commission,

    round((price * qty)::numeric, 6) as notional,

    case
        when side = 'BUY' then round((-price * qty - coalesce(commission, 0))::numeric, 6)
        when side = 'SELL' then round((price * qty - coalesce(commission, 0))::numeric, 6)
        else 0
    end as signed_cashflow,

    case
        when price > 0 then round((coalesce(commission, 0) / nullif(price * qty, 0))::numeric, 8)
        else null
    end as commission_pct,

    payload
from trades
where origin in ('paper', 'real_dry_run', 'replay');
