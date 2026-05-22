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

    CASE
        WHEN b.new_profit_factor >= 3 THEN 'ELITE'
        WHEN b.new_profit_factor >= 2 THEN 'STRONG'
        WHEN b.new_profit_factor >= 1.3 THEN 'PROMISING'
        ELSE 'WEAK'
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
   AND r.policy_name = b.policy_name;
