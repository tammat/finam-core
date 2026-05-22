CREATE OR REPLACE VIEW v_exit_alpha_radar_dashboard AS
SELECT
    r.symbol,
    r.strategy,
    r.timeframe,
    r.trade_source,
    r.policy_name,

    r.radar_enabled,
    r.runtime_enabled,

    b.new_profit_factor AS exit_alpha_pf,
    b.new_expectancy AS exit_alpha_expectancy,
    b.evaluated_trades,
    b.no_bars_trades,
    b.delta_expectancy,

    s.trades AS raw_trades,
    s.profit_factor AS raw_profit_factor,
    s.expectancy AS raw_expectancy,
    s.winrate AS raw_winrate,
    s.status AS raw_status,

    g.bias_alignment,
    g.volatility_state,
    g.allow_runtime AS futures_allow_runtime,
    g.allow_paper AS futures_allow_paper,

    r.reason,
    r.created_at
FROM strategy_exit_alpha_radar r
LEFT JOIN strategy_best_exit_alpha_policy b
  ON b.symbol = r.symbol
 AND b.strategy = r.strategy
 AND b.timeframe = r.timeframe
 AND b.trade_source = r.trade_source
LEFT JOIN strategy_statistics_v2 s
  ON s.symbol = r.symbol
 AND s.strategy = r.strategy
 AND s.timeframe = r.timeframe
 AND s.trade_source = r.trade_source
LEFT JOIN futures_regime_governance g
  ON g.symbol = r.symbol;
