DROP VIEW IF EXISTS directional_edge_guard_v1;

CREATE VIEW directional_edge_guard_v1 AS
WITH direction_summary AS (
    SELECT
        continuous_symbol,
        symbol,
        strategy,
        timeframe,
        trade_source,
        regime_direction,

        SUM(closed_trades) AS closed_trades,
        SUM(wins) AS wins,
        SUM(losses) AS losses,
        SUM(net_pnl) AS net_pnl,

        ROUND((SUM(wins)::numeric / NULLIF(SUM(closed_trades), 0)), 4) AS winrate,
        ROUND((SUM(net_pnl)::numeric / NULLIF(SUM(closed_trades), 0)), 4) AS expectancy,

        MIN(first_entry_ts) AS first_entry_ts,
        MAX(last_exit_ts) AS last_exit_ts
    FROM regime_scorecard_v1
    WHERE regime_direction IN ('trend_up', 'trend_down')
    GROUP BY
        continuous_symbol,
        symbol,
        strategy,
        timeframe,
        trade_source,
        regime_direction
)
SELECT
    continuous_symbol,
    symbol,
    strategy,
    timeframe,
    trade_source,
    regime_direction,
    closed_trades,
    wins,
    losses,
    winrate,
    ROUND(net_pnl::numeric, 4) AS net_pnl,
    expectancy,

    CASE
        WHEN closed_trades < 20 THEN 'insufficient_data'
        WHEN expectancy > 0 AND net_pnl > 0 THEN 'favorable'
        WHEN expectancy < 0 AND net_pnl < 0 THEN 'unfavorable'
        ELSE 'neutral'
    END AS directional_edge_status,

    CASE
        WHEN closed_trades < 20 THEN 'sample_below_min_20'
        WHEN expectancy > 0 AND net_pnl > 0 THEN 'positive_expectancy_and_positive_net_pnl'
        WHEN expectancy < 0 AND net_pnl < 0 THEN 'negative_expectancy_and_negative_net_pnl'
        ELSE 'mixed_or_flat_result'
    END AS directional_edge_reason,

    'analytics_only' AS guard_mode,

    first_entry_ts,
    last_exit_ts
FROM direction_summary;
