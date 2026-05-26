DROP VIEW IF EXISTS session_scorecard_v1;

CREATE VIEW session_scorecard_v1 AS
WITH base AS (
    SELECT
        continuous_symbol,
        symbol,
        strategy,
        timeframe,
        trade_source,
        EXTRACT(HOUR FROM COALESCE(entry_ts, created_at))::int AS hour_utc,
        CASE
            WHEN EXTRACT(HOUR FROM COALESCE(entry_ts, created_at))::int BETWEEN 0 AND 5 THEN 'asia'
            WHEN EXTRACT(HOUR FROM COALESCE(entry_ts, created_at))::int BETWEEN 6 AND 9 THEN 'europe_open'
            WHEN EXTRACT(HOUR FROM COALESCE(entry_ts, created_at))::int BETWEEN 10 AND 13 THEN 'europe_mid'
            WHEN EXTRACT(HOUR FROM COALESCE(entry_ts, created_at))::int BETWEEN 14 AND 17 THEN 'us_overlap'
            ELSE 'late_session'
        END AS session_bucket,
        net_pnl,
        holding_seconds
    FROM trade_outcomes
)
SELECT
    continuous_symbol,
    symbol,
    strategy,
    timeframe,
    trade_source,
    session_bucket,
    hour_utc,

    COUNT(*) AS closed_trades,
    COUNT(*) FILTER (WHERE net_pnl > 0) AS wins,
    COUNT(*) FILTER (WHERE net_pnl < 0) AS losses,

    ROUND((COUNT(*) FILTER (WHERE net_pnl > 0)::numeric / NULLIF(COUNT(*), 0)), 4) AS winrate,
    ROUND(SUM(net_pnl)::numeric, 4) AS net_pnl,
    ROUND(AVG(net_pnl)::numeric, 4) AS expectancy,
    ROUND(AVG(net_pnl) FILTER (WHERE net_pnl > 0)::numeric, 4) AS avg_win,
    ROUND(AVG(net_pnl) FILTER (WHERE net_pnl < 0)::numeric, 4) AS avg_loss,
    ROUND((SUM(net_pnl) FILTER (WHERE net_pnl > 0)::numeric / NULLIF(ABS(SUM(net_pnl) FILTER (WHERE net_pnl < 0))::numeric, 0)), 4) AS profit_factor,
    ROUND(AVG(holding_seconds / 60.0)::numeric, 2) AS avg_holding_minutes,

    CASE
        WHEN COUNT(*) < 5 THEN 'insufficient_data'
        WHEN SUM(net_pnl) > 0 AND AVG(net_pnl) > 0 THEN 'favorable'
        WHEN SUM(net_pnl) < 0 AND AVG(net_pnl) < 0 THEN 'unfavorable'
        ELSE 'neutral'
    END AS session_edge_status
FROM base
GROUP BY
    continuous_symbol, symbol, strategy, timeframe, trade_source, session_bucket, hour_utc;
