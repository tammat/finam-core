create or replace view analytics_strategy_performance_monitor_v2 as
select
    analytics_symbol,
    strategy,

    count(*) as closed_trades,

    round(sum(net_pnl)::numeric, 6) as total_net_pnl,
    round(avg(net_pnl)::numeric, 6) as expectancy,

    round(avg(return_pct)::numeric, 8) as avg_return_pct,

    round(avg(is_win)::numeric, 4) as winrate,

    round(
        (
            sum(case when net_pnl > 0 then net_pnl else 0 end)
            / nullif(abs(sum(case when net_pnl < 0 then net_pnl else 0 end)), 0)
        )::numeric,
        4
    ) as profit_factor,

    round(min(net_pnl)::numeric, 6) as worst_trade,
    round(max(net_pnl)::numeric, 6) as best_trade,

    min(entry_ts) as first_trade_ts,
    max(exit_ts) as last_trade_ts,

    round(
        stddev_samp(net_pnl)::numeric,
        6
    ) as pnl_stddev

from analytics_closed_trades_normalized
group by analytics_symbol, strategy;
