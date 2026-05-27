DROP VIEW IF EXISTS v_today_pnl_summary_ru;
DROP VIEW IF EXISTS v_today_trades_ru;
DROP VIEW IF EXISTS v_today_trade_pnl_calc;

CREATE VIEW v_today_trade_pnl_calc AS
SELECT
    ts,
    symbol,
    side,
    qty::numeric AS qty,
    price::numeric AS price,
    position_qty_after::numeric AS position_qty_after,
    avg_price_after::numeric AS avg_price_after,
    trade_pnl::numeric AS trade_pnl
FROM analytics_intraday_pnl
WHERE trade_date = (now() AT TIME ZONE 'Europe/Moscow')::date
ORDER BY ts;

CREATE VIEW v_today_trades_ru AS
SELECT
    p.ts AS "Время",
    COALESCE(NULLIF(i.short_name, ''), NULLIF(i.display_name, ''), p.symbol) AS "Название",
    p.symbol AS "Тикер",
    CASE p.side
        WHEN 'BUY' THEN 'Покупка'
        WHEN 'SELL' THEN 'Продажа'
        ELSE p.side
    END AS "Операция",
    p.qty AS "Количество",
    p.price AS "Цена",
    round(p.position_qty_after::numeric, 6) AS "Позиция после",
    round(p.avg_price_after::numeric, 6) AS "Средняя цена после",
    round(p.trade_pnl::numeric, 6) AS "P&L"
FROM analytics_intraday_pnl p
LEFT JOIN instrument_reference i ON i.symbol = p.symbol
WHERE p.trade_date = CURRENT_DATE
ORDER BY p.ts DESC;

CREATE VIEW v_today_pnl_summary_ru AS
SELECT
    now() AS "Время",
    (now() AT TIME ZONE 'Europe/Moscow')::date AS "Дата",
    round(COALESCE(sum(trade_pnl), 0)::numeric, 2) AS "P&L за день",
    count(*) AS "Сделок",
    count(DISTINCT symbol) AS "Инструментов"
FROM analytics_intraday_pnl
WHERE trade_date = (now() AT TIME ZONE 'Europe/Moscow')::date;
