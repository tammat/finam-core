CREATE OR REPLACE VIEW v_strategy_statistics_futures_grafana AS
SELECT
    COALESCE(f.root_symbol, s.symbol) AS "Базовый инструмент",
    s.symbol AS "Контракт",
    f.expiration_date AS "Дата экспирации",
    f.days_to_expiration AS "Дней до экспирации",
    COALESCE(f.status, 'UNKNOWN') AS "Статус контракта",

    s.strategy AS "Стратегия",
    s.timeframe AS "Таймфрейм",
    s.trade_source AS "Источник",

    s.trades AS "Сделок",
    ROUND(s.profit_factor::numeric, 4) AS "PF",
    ROUND(s.winrate::numeric, 4) AS "Winrate",
    ROUND(s.expectancy::numeric, 6) AS "Expectancy",

    ROUND(s.quality_full_ratio::numeric, 4) AS "Полный контекст",
    ROUND(s.quality_partial_ratio::numeric, 4) AS "Частичный контекст",
    s.status AS "Статус стратегии",
    s.calculated_at AS "Обновлено"
FROM strategy_statistics_v2 s
JOIN futures_context_snapshots f
  ON f.contract_symbol = s.symbol
ORDER BY
    COALESCE(f.root_symbol, s.symbol),
    f.expiration_date NULLS FIRST,
    s.strategy,
    s.timeframe;
