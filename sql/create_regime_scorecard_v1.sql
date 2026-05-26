CREATE OR REPLACE VIEW regime_scorecard_v1 AS
WITH enriched AS (
    SELECT
        t.continuous_symbol,
        t.symbol,
        t.strategy,
        t.timeframe,
        t.trade_source,

        lower(COALESCE(
            NULLIF(t.raw_json->'entry_payload'->'market'->>'regime_direction', ''),
            NULLIF(t.raw_json->'entry_payload'->>'regime_direction', ''),
            NULLIF(t.raw_json->'entry_payload'->>'regime', ''),
            NULLIF(t.raw_json->'entry_payload'->>'regime_label', ''),
            'unknown'
        )) AS regime_direction,

        CASE
            WHEN NULLIF(t.raw_json->'entry_payload'->'market'->>'regime_direction', '') IS NOT NULL THEN 'snapshot.market.regime_direction'
            WHEN NULLIF(t.raw_json->'entry_payload'->>'regime_direction', '') IS NOT NULL THEN 'entry_payload.regime_direction'
            WHEN NULLIF(t.raw_json->'entry_payload'->>'regime', '') IS NOT NULL THEN 'entry_payload.regime'
            WHEN NULLIF(t.raw_json->'entry_payload'->>'regime_label', '') IS NOT NULL THEN 'entry_payload.regime_label'
            ELSE 'missing'
        END AS regime_source,

        COALESCE(
            t.raw_json->'entry_payload'->'risk'->'edge_gate'->>'reason',
            t.raw_json->'entry_payload'->'trade_context_snapshot'->'edge_gate'->>'reason',
            t.raw_json->'entry_payload'->'edge_gate'->>'reason',
            t.raw_json->'entry_payload'->>'edge_reason',
            'unknown'
        ) AS edge_reason,

        EXTRACT(HOUR FROM t.entry_ts) AS hour_utc,

        t.net_pnl,
        t.gross_pnl,
        t.holding_seconds,
        t.entry_ts,
        t.exit_ts
    FROM trade_outcomes t
),
base AS (
    SELECT
        continuous_symbol,
        symbol,
        strategy,
        timeframe,
        trade_source,
        regime_direction,
        regime_source,
        edge_reason,
        hour_utc,

        COUNT(*) AS closed_trades,
        COUNT(*) FILTER (WHERE net_pnl > 0) AS wins,
        COUNT(*) FILTER (WHERE net_pnl < 0) AS losses,

        SUM(net_pnl) AS net_pnl,
        AVG(net_pnl) AS expectancy,

        AVG(net_pnl) FILTER (WHERE net_pnl > 0) AS avg_win,
        AVG(net_pnl) FILTER (WHERE net_pnl < 0) AS avg_loss,

        SUM(net_pnl) FILTER (WHERE net_pnl > 0) AS gross_win,
        ABS(SUM(net_pnl) FILTER (WHERE net_pnl < 0)) AS gross_loss,

        AVG(holding_seconds) AS avg_holding_seconds,

        MIN(entry_ts) AS first_entry_ts,
        MAX(exit_ts) AS last_exit_ts
    FROM enriched
    GROUP BY
        continuous_symbol,
        symbol,
        strategy,
        timeframe,
        trade_source,
        regime_direction,
        regime_source,
        edge_reason,
        hour_utc
)
SELECT
    continuous_symbol,
    symbol,
    strategy,
    timeframe,
    trade_source,
    regime_direction,
    regime_source,
    edge_reason,
    hour_utc,
    (regime_direction <> 'unknown') AS regime_known,
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
    ROUND((avg_holding_seconds::numeric / 60.0), 2) AS avg_holding_minutes,
    first_entry_ts,
    last_exit_ts
FROM base;
