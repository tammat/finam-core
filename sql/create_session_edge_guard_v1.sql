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
    hour_msk,

    closed_trades,
    wins,
    losses,

    winrate,
    net_pnl,
    expectancy,
    profit_factor,

    session_edge_status,

    CASE
        WHEN session_edge_status = 'благоприятно'
             AND expectancy > 0
             AND profit_factor >= 1.2
        THEN 'подтверждено'

        WHEN session_edge_status = 'неблагоприятно'
             AND expectancy < 0
        THEN 'несоответствие'

        WHEN session_edge_status = 'недостаточно_данных'
        THEN 'недостаточно_данных'

        ELSE 'нейтрально'
    END AS advisory_status,

    CASE
        WHEN session_edge_status = 'благоприятно'
             AND expectancy > 0
             AND profit_factor >= 1.2
        THEN 'СЕССИОННЫЙ_EDGE_ПОДТВЕРЖДЕН'

        WHEN session_edge_status = 'неблагоприятно'
             AND expectancy < 0
        THEN 'СЕССИОННЫЙ_EDGE_НЕСООТВЕТСТВИЕ'

        WHEN session_edge_status = 'недостаточно_данных'
        THEN 'СЕССИОННЫЙ_EDGE_НЕДОСТАТОЧНО_ДАННЫХ'

        ELSE 'СЕССИОННЫЙ_EDGE_НЕЙТРАЛЬНО'
    END AS advisory_reason,

    'только_аналитика' AS guard_mode

FROM session_scorecard_v1;
