create or replace view analytics_closed_trades_normalized as
with ordered as (
    select
        ts_msk,
        execution_symbol,
        analytics_symbol,
        strategy,
        side,
        qty,
        price,
        signed_cashflow,
        row_number() over (
            partition by analytics_symbol, strategy
            order by ts_msk
        ) as rn
    from analytics_trades_normalized
),

paired as (
    select
        b.analytics_symbol,
        b.strategy,

        b.ts_msk as entry_ts,
        s.ts_msk as exit_ts,

        b.execution_symbol as entry_symbol,
        s.execution_symbol as exit_symbol,

        b.price as entry_price,
        s.price as exit_price,

        b.qty as qty,

        abs(b.signed_cashflow) as entry_cashflow,
        s.signed_cashflow as exit_cashflow,

        (
            s.signed_cashflow - abs(b.signed_cashflow)
        ) as net_pnl

    from ordered b
    join ordered s
      on s.analytics_symbol = b.analytics_symbol
     and s.strategy = b.strategy
     and s.rn = b.rn + 1

    where b.side = 'BUY'
      and s.side = 'SELL'
)

select
    analytics_symbol,
    strategy,

    entry_ts,
    exit_ts,

    entry_symbol,
    exit_symbol,

    qty,

    round(entry_price::numeric, 6) as entry_price,
    round(exit_price::numeric, 6) as exit_price,

    round(net_pnl::numeric, 6) as net_pnl,

    round(
        (
            (exit_price - entry_price)
            / nullif(entry_price, 0)
        )::numeric,
        6
    ) as return_pct,

    extract(epoch from (exit_ts - entry_ts)) as holding_seconds,

    case
        when net_pnl > 0 then 1
        else 0
    end as is_win

from paired;
