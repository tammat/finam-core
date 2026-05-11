CREATE OR REPLACE VIEW v_today_trade_pnl_calc AS
WITH trades_today AS (
    SELECT
        t.ts,
        t.symbol,
        UPPER(t.side) AS side,
        t.qty::numeric AS qty,
        t.price::numeric AS price
    FROM trades t
    WHERE t.ts::date = CURRENT_DATE
),
ordered AS (
    SELECT
        *,
        SUM(CASE WHEN side = 'BUY' THEN qty ELSE 0 END)
            OVER (
                PARTITION BY symbol
                ORDER BY ts
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ) AS buy_qty_before,
        SUM(CASE WHEN side = 'BUY' THEN qty * price ELSE 0 END)
            OVER (
                PARTITION BY symbol
                ORDER BY ts
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ) AS buy_amount_before
    FROM trades_today
),
calc AS (
    SELECT
        ts,
        symbol,
        side,
        qty,
        price,
        COALESCE(buy_qty_before, 0) AS buy_qty_before,
        COALESCE(buy_amount_before, 0) AS buy_amount_before,
        CASE
            WHEN COALESCE(buy_qty_before, 0) > 0
            THEN COALESCE(buy_amount_before, 0) / COALESCE(buy_qty_before, 0)
            ELSE NULL
        END AS avg_entry_price_before,
        CASE
            WHEN side = 'SELL' AND COALESCE(buy_qty_before, 0) > 0
            THEN qty * (
                price - (
                    COALESCE(buy_amount_before, 0) / COALESCE(buy_qty_before, 0)
                )
            )
            ELSE 0::numeric
        END AS trade_pnl
    FROM ordered
)
SELECT
    *
FROM calc;

CREATE OR REPLACE VIEW v_today_trades_ru AS
SELECT
    c.ts AS "Время",
    COALESCE(NULLIF(i.short_name, ''), NULLIF(i.display_name, ''), c.symbol) AS "Название",
    c.symbol AS "Тикер",
    CASE c.side
        WHEN 'BUY' THEN 'Вход / покупка'
        WHEN 'SELL' THEN 'Выход / продажа'
        ELSE c.side
    END AS "Операция",
    c.qty AS "Количество",
    c.price AS "Цена",
    COALESCE(c.avg_entry_price_before, 0) AS "Средняя цена входа",
    ROUND(c.trade_pnl, 2) AS "P&L сделки",
    ROUND(
        SUM(c.trade_pnl) OVER (
            PARTITION BY c.symbol
            ORDER BY c.ts
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS "P&L накопленный"
FROM v_today_trade_pnl_calc c
LEFT JOIN instrument_reference i ON i.symbol = c.symbol
ORDER BY c.ts DESC;

CREATE OR REPLACE VIEW v_position_chart_ru AS
SELECT
    c.ts AS "Время",
    COALESCE(NULLIF(i.short_name, ''), NULLIF(i.display_name, ''), c.symbol) AS "Название",
    c.symbol AS "Тикер",
    c.price AS "Цена",
    CASE c.side
        WHEN 'BUY' THEN 'Вход'
        WHEN 'SELL' THEN 'Выход'
        ELSE c.side
    END AS "Событие",
    c.qty AS "Количество",
    ROUND(c.trade_pnl, 2) AS "P&L сделки",
    ROUND(
        SUM(c.trade_pnl) OVER (
            PARTITION BY c.symbol
            ORDER BY c.ts
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS "P&L накопленный"
FROM v_today_trade_pnl_calc c
LEFT JOIN instrument_reference i ON i.symbol = c.symbol
ORDER BY c.ts ASC;

CREATE OR REPLACE VIEW v_today_pnl_summary_ru AS
SELECT
    now() AS "Время",
    ROUND(COALESCE(SUM(trade_pnl), 0), 2) AS "P&L за день",
    COUNT(*) AS "Сделок",
    COUNT(DISTINCT symbol) AS "Инструментов"
FROM v_today_trade_pnl_calc;

CREATE OR REPLACE VIEW v_today_pnl_by_symbol_ru AS
SELECT
    COALESCE(NULLIF(i.short_name, ''), NULLIF(i.display_name, ''), c.symbol) AS "Название",
    c.symbol AS "Тикер",
    ROUND(SUM(c.trade_pnl), 2) AS "P&L за день",
    COUNT(*) AS "Сделок"
FROM v_today_trade_pnl_calc c
LEFT JOIN instrument_reference i ON i.symbol = c.symbol
GROUP BY
    COALESCE(NULLIF(i.short_name, ''), NULLIF(i.display_name, ''), c.symbol),
    c.symbol
ORDER BY "P&L за день" DESC;
