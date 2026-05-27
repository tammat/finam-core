CREATE OR REPLACE VIEW v_today_rejected_trades_ru AS
SELECT
    t.ts AS "Время UTC",
    t.ts AT TIME ZONE 'Europe/Moscow' AS "Время МСК",
    t.symbol AS "Инструмент",
    t.side AS "Операция",
    t.qty AS "Количество",
    t.price AS "Цена",
    t.trade_source AS "Источник",
    t.strategy AS "Стратегия",
    t.timeframe AS "Таймфрейм",
    t.invalid_reason AS "Причина отклонения",
    t.payload AS "Payload"
FROM trades t
WHERE (t.ts AT TIME ZONE 'Europe/Moscow')::date = (now() AT TIME ZONE 'Europe/Moscow')::date
  AND t.is_invalid = true
ORDER BY t.ts DESC;

CREATE OR REPLACE VIEW v_today_rejected_trades_summary_ru AS
SELECT
    (now() AT TIME ZONE 'Europe/Moscow')::date AS "Дата МСК",
    invalid_reason AS "Причина отклонения",
    count(*) AS "Количество",
    count(DISTINCT symbol) AS "Инструментов",
    count(DISTINCT strategy) AS "Стратегий"
FROM trades
WHERE (ts AT TIME ZONE 'Europe/Moscow')::date = (now() AT TIME ZONE 'Europe/Moscow')::date
  AND is_invalid = true
GROUP BY invalid_reason
ORDER BY count(*) DESC;
