DROP VIEW IF EXISTS session_edge_guard_v1;

CREATE VIEW session_edge_guard_v1 AS
SELECT
    continuous_symbol,
    symbol,
    strategy,
    timeframe,
    trade_source,

    session_bucket,
    hour_utc,

    closed_trades,
    wins,
    losses,

    winrate,
    net_pnl,
    expectancy,
    profit_factor,

    session_edge_status,

    CASE
        WHEN session_edge_status = 'favorable'
             AND expectancy > 0
             AND profit_factor >= 1.2
        THEN 'confirmed'

        WHEN session_edge_status = 'unfavorable'
             AND expectancy < 0
        THEN 'mismatch'

        WHEN session_edge_status = 'insufficient_data'
        THEN 'insufficient_data'

        ELSE 'neutral'
    END AS advisory_status,

    CASE
        WHEN session_edge_status = 'favorable'
             AND expectancy > 0
             AND profit_factor >= 1.2
        THEN 'SESSION_EDGE_CONFIRMED'

        WHEN session_edge_status = 'unfavorable'
             AND expectancy < 0
        THEN 'SESSION_EDGE_MISMATCH'

        WHEN session_edge_status = 'insufficient_data'
        THEN 'SESSION_EDGE_INSUFFICIENT_DATA'

        ELSE 'SESSION_EDGE_NEUTRAL'
    END AS advisory_reason,

    'analytics_only' AS guard_mode

FROM session_scorecard_v1;
