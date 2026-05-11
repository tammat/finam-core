CREATE OR REPLACE VIEW v_today_trades_ru AS
SELECT
    t.ts AS "Время",
    COALESCE(NULLIF(i.short_name, ''), NULLIF(i.display_name, ''), t.symbol) AS "Название",
    t.symbol AS "Тикер",
    CASE t.side
        WHEN 'BUY' THEN 'Вход / покупка'
        WHEN 'SELL' THEN 'Выход / продажа'
        ELSE t.side
    END AS "Операция",
    t.qty AS "Количество",
    t.price AS "Цена",
    0::numeric AS "P&L"
FROM trades t
LEFT JOIN instrument_reference i ON i.symbol = t.symbol
WHERE t.ts::date = CURRENT_DATE
ORDER BY t.ts DESC;

CREATE OR REPLACE VIEW v_position_chart_ru AS
SELECT
    t.ts AS "Время",
    COALESCE(NULLIF(i.short_name, ''), NULLIF(i.display_name, ''), t.symbol) AS "Название",
    t.symbol AS "Тикер",
    t.price AS "Цена",
    CASE t.side
        WHEN 'BUY' THEN 'Вход'
        WHEN 'SELL' THEN 'Выход'
        ELSE t.side
    END AS "Событие",
    t.qty AS "Количество",
    0::numeric AS "P&L"
FROM trades t
LEFT JOIN instrument_reference i ON i.symbol = t.symbol
WHERE t.ts::date = CURRENT_DATE
ORDER BY t.ts ASC;
