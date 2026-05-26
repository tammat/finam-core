CREATE OR REPLACE VIEW strategy_scorecard_v1 AS
WITH base AS (
    SELECT
        continuous_symbol,
        symbol,
        strategy,
        timeframe,
        trade_source,
        COUNT(*) AS closed_trades,
        COUNT(*) FILTER (WHERE net_pnl > 0) AS wins,
        COUNT(*) FILTER (WHERE net_pnl < 0) AS losses,
        COUNT(*) FILTER (WHERE net_pnl = 0) AS flats,
        SUM(gross_pnl) AS gross_pnl,
        SUM(commission) AS commission,
        SUM(net_pnl) AS net_pnl,
        AVG(net_pnl) AS expectancy,
        AVG(net_pnl) FILTER (WHERE net_pnl > 0) AS avg_win,
        AVG(net_pnl) FILTER (WHERE net_pnl < 0) AS avg_loss,
        SUM(net_pnl) FILTER (WHERE net_pnl > 0) AS gross_win,
        ABS(SUM(net_pnl) FILTER (WHERE net_pnl < 0)) AS gross_loss,
        AVG(holding_seconds) AS avg_holding_seconds,
        MIN(entry_ts) AS first_entry_ts,
        MAX(exit_ts) AS last_exit_ts
    FROM trade_outcomes
    GROUP BY
        continuous_symbol,
        symbol,
        strategy,
        timeframe,
        trade_source
)
SELECT
    continuous_symbol,
    symbol,
    strategy,
    timeframe,
    trade_source,
    closed_trades,
    wins,
    losses,
    flats,
    ROUND((wins::numeric / NULLIF(closed_trades, 0)), 4) AS winrate,
    ROUND(gross_pnl::numeric, 4) AS gross_pnl,
    ROUND(commission::numeric, 4) AS commission,
    ROUND(net_pnl::numeric, 4) AS net_pnl,
    ROUND(expectancy::numeric, 4) AS expectancy,
    ROUND(avg_win::numeric, 4) AS avg_win,
    ROUND(avg_loss::numeric, 4) AS avg_loss,
    ROUND((gross_win::numeric / NULLIF(gross_loss::numeric, 0)), 4) AS profit_factor,
    ROUND((avg_win::numeric / NULLIF(ABS(avg_loss::numeric), 0)), 4) AS payoff_ratio,
    ROUND((avg_holding_seconds::numeric / 60.0), 2) AS avg_holding_minutes,
    first_entry_ts,
    last_exit_ts
FROM base;
