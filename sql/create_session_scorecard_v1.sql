DROP VIEW IF EXISTS session_edge_guard_v1;
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
        EXTRACT(HOUR FROM COALESCE(entry_ts, created_at) AT TIME ZONE 'Europe/Moscow')::int AS hour_msk,

        CASE
            WHEN EXTRACT(HOUR FROM COALESCE(entry_ts, created_at) AT TIME ZONE 'Europe/Moscow')::int BETWEEN 3 AND 8
                THEN 'азиатская_сессия'
            WHEN EXTRACT(HOUR FROM COALESCE(entry_ts, created_at) AT TIME ZONE 'Europe/Moscow')::int BETWEEN 9 AND 12
                THEN 'московское_открытие'
            WHEN EXTRACT(HOUR FROM COALESCE(entry_ts, created_at) AT TIME ZONE 'Europe/Moscow')::int BETWEEN 13 AND 16
                THEN 'московская_середина'
            WHEN EXTRACT(HOUR FROM COALESCE(entry_ts, created_at) AT TIME ZONE 'Europe/Moscow')::int BETWEEN 17 AND 23
                THEN 'вечерняя_сессия'
            ELSE 'поздняя_сессия'
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
    hour_msk,

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
        WHEN COUNT(*) < 5 THEN 'недостаточно_данных'
        WHEN SUM(net_pnl) > 0 AND AVG(net_pnl) > 0 THEN 'благоприятно'
        WHEN SUM(net_pnl) < 0 AND AVG(net_pnl) < 0 THEN 'неблагоприятно'
        ELSE 'нейтрально'
    END AS session_edge_status
FROM base
GROUP BY
    continuous_symbol,
    symbol,
    strategy,
    timeframe,
    trade_source,
    session_bucket,
    hour_utc,
    hour_msk;
