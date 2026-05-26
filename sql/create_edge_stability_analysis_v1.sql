DROP VIEW IF EXISTS edge_stability_analysis_v1;

CREATE VIEW edge_stability_analysis_v1 AS
WITH ordered AS (
    SELECT
        o.*,
        ntile(4) OVER (
            PARTITION BY o.continuous_symbol, o.strategy, o.timeframe, o.trade_source
            ORDER BY COALESCE(o.entry_ts, o.created_at), o.id
        ) AS edge_quartile
    FROM trade_outcomes o
),
bucketed AS (
    SELECT
        continuous_symbol,
        symbol,
        strategy,
        timeframe,
        trade_source,
        edge_quartile,

        COUNT(*) AS closed_trades,
        COUNT(*) FILTER (WHERE net_pnl > 0) AS wins,
        COUNT(*) FILTER (WHERE net_pnl < 0) AS losses,

        SUM(net_pnl) AS net_pnl,
        AVG(net_pnl) AS expectancy,

        AVG(net_pnl) FILTER (WHERE net_pnl > 0) AS avg_win,
        AVG(net_pnl) FILTER (WHERE net_pnl < 0) AS avg_loss,

        SUM(net_pnl) FILTER (WHERE net_pnl > 0) AS gross_win,
        ABS(SUM(net_pnl) FILTER (WHERE net_pnl < 0)) AS gross_loss,

        MIN(entry_ts) AS first_entry_ts,
        MAX(exit_ts) AS last_exit_ts
    FROM ordered
    GROUP BY
        continuous_symbol,
        symbol,
        strategy,
        timeframe,
        trade_source,
        edge_quartile
),
summary AS (
    SELECT
        b.*,
        FIRST_VALUE(expectancy) OVER (
            PARTITION BY continuous_symbol, strategy, timeframe, trade_source
            ORDER BY edge_quartile
        ) AS first_expectancy,
        LAST_VALUE(expectancy) OVER (
            PARTITION BY continuous_symbol, strategy, timeframe, trade_source
            ORDER BY edge_quartile
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS last_expectancy
    FROM bucketed b
)
SELECT
    continuous_symbol,
    symbol,
    strategy,
    timeframe,
    trade_source,
    edge_quartile,
    closed_trades,
    wins,
    losses,
    ROUND((wins::numeric / NULLIF(closed_trades, 0)), 4) AS winrate,
    ROUND(net_pnl::numeric, 4) AS net_pnl,
    ROUND(expectancy::numeric, 4) AS expectancy,
    ROUND(avg_win::numeric, 4) AS avg_win,
    ROUND(avg_loss::numeric, 4) AS avg_loss,
    ROUND(gross_win::numeric / NULLIF(gross_loss::numeric, 0), 4) AS profit_factor,
    ROUND(avg_win::numeric / NULLIF(ABS(avg_loss::numeric), 0), 4) AS payoff_ratio,
    ROUND(first_expectancy::numeric, 4) AS first_expectancy,
    ROUND(last_expectancy::numeric, 4) AS last_expectancy,
    CASE
        WHEN closed_trades < 5 THEN 'insufficient_bucket_data'
        WHEN last_expectancy < 0 AND first_expectancy > 0 THEN 'unstable_sign_flip'
        WHEN first_expectancy > 0 AND last_expectancy < first_expectancy * 0.5 THEN 'degrading'
        WHEN expectancy > 0 THEN 'stable_positive'
        WHEN expectancy < 0 THEN 'stable_negative'
        ELSE 'neutral'
    END AS stability_status,
    CASE
        WHEN closed_trades < 5 THEN 'bucket_sample_below_5'
        WHEN last_expectancy < 0 AND first_expectancy > 0 THEN 'expectancy_flipped_positive_to_negative'
        WHEN first_expectancy > 0 AND last_expectancy < first_expectancy * 0.5 THEN 'last_expectancy_below_half_first'
        WHEN expectancy > 0 THEN 'positive_expectancy_bucket'
        WHEN expectancy < 0 THEN 'negative_expectancy_bucket'
        ELSE 'flat_expectancy_bucket'
    END AS stability_reason,
    first_entry_ts,
    last_exit_ts
FROM summary;
