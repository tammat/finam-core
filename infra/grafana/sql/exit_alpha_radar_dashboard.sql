DROP VIEW IF EXISTS v_exit_alpha_radar_dashboard CASCADE;

CREATE OR REPLACE VIEW v_exit_alpha_radar_dashboard AS
SELECT
    b.symbol,
    b.strategy,
    b.timeframe,
    b.trade_source,
    b.policy_name,

    round(b.new_profit_factor::numeric, 6) AS exit_alpha_pf,
    round(b.new_expectancy::numeric, 6) AS exit_alpha_expectancy,
    round(b.delta_expectancy::numeric, 6) AS delta_expectancy,

    round(s.profit_factor::numeric, 6) AS raw_profit_factor,
    round(s.expectancy::numeric, 6) AS raw_expectancy,
    round(s.winrate::numeric, 6) AS raw_winrate,
    s.trades AS raw_trades,
    s.status AS raw_status,

    b.evaluated_trades,
    b.no_bars_trades,

    b.stop_atr,
    b.take_atr,
    b.trail_atr,
    b.max_bars_held,

    sa.session_bucket AS best_session_bucket,
    round(sa.profit_factor::numeric, 6) AS session_pf,
    round(sa.expectancy::numeric, 6) AS session_expectancy,
    round(sa.winrate::numeric, 6) AS session_winrate,
    sa.trades AS session_trades,

    CASE
        WHEN b.new_profit_factor >= 3 THEN 'ЭЛИТНАЯ'
        WHEN b.new_profit_factor >= 2 THEN 'СИЛЬНАЯ'
        WHEN b.new_profit_factor >= 1.3 THEN 'ПЕРСПЕКТИВНАЯ'
        ELSE 'СЛАБАЯ'
    END AS exit_alpha_quality,

    (b.new_expectancy > 0) AS expectancy_positive,

    r.radar_enabled,
    r.runtime_enabled,
    r.reason,
    b.selected_at AS calculated_at

FROM strategy_best_exit_alpha_policy b
LEFT JOIN strategy_statistics_v2 s
    ON s.symbol = b.symbol
   AND s.strategy = b.strategy
   AND s.timeframe = b.timeframe
   AND s.trade_source = b.trade_source
LEFT JOIN strategy_exit_alpha_radar r
    ON r.symbol = b.symbol
   AND r.strategy = b.strategy
   AND r.timeframe = b.timeframe
   AND r.trade_source = b.trade_source
   AND r.policy_name = b.policy_name
LEFT JOIN LATERAL (
    SELECT x.*
    FROM futures_session_trade_analytics x
    WHERE x.symbol = b.symbol
      AND x.strategy = b.strategy
      AND x.timeframe = b.timeframe
      AND x.trade_source = b.trade_source
    ORDER BY x.profit_factor DESC, x.expectancy DESC, x.trades DESC
    LIMIT 1
) sa ON TRUE;
