CREATE OR REPLACE VIEW v_today_trade_pnl_calc AS
WITH trades_today AS (
    SELECT
        t.ts,
        t.symbol,
        upper(t.side) AS side,
        t.qty::numeric AS qty,
        t.price::numeric AS price
    FROM trades t
    WHERE t.ts::date = CURRENT_DATE
      AND t.is_invalid = false
),
ordered AS (
    SELECT
        t.*,

        COALESCE(sum(CASE WHEN side = 'BUY' THEN qty ELSE 0 END)
            OVER (PARTITION BY symbol ORDER BY ts ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS buy_qty_before,

        COALESCE(sum(CASE WHEN side = 'BUY' THEN qty * price ELSE 0 END)
            OVER (PARTITION BY symbol ORDER BY ts ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS buy_amount_before,

        COALESCE(sum(CASE WHEN side = 'SELL' THEN qty ELSE 0 END)
            OVER (PARTITION BY symbol ORDER BY ts ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS sell_qty_before,

        COALESCE(sum(CASE WHEN side = 'SELL' THEN qty * price ELSE 0 END)
            OVER (PARTITION BY symbol ORDER BY ts ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS sell_amount_before
    FROM trades_today t
),
calc AS (
    SELECT
        ts,
        symbol,
        side,
        qty,
        price,
        buy_qty_before,
        buy_amount_before,
        CASE WHEN buy_qty_before > 0 THEN buy_amount_before / buy_qty_before END AS avg_entry_price_before,
        CASE WHEN sell_qty_before > 0 THEN sell_amount_before / sell_qty_before END AS avg_short_price_before,

        CASE
            -- Закрытие long: раньше были покупки, сейчас продажа.
            WHEN side = 'SELL' AND buy_qty_before > 0
                THEN qty * (price - buy_amount_before / buy_qty_before)

            -- Закрытие short: раньше были продажи, сейчас покупка.
            WHEN side = 'BUY' AND sell_qty_before > 0
                THEN qty * (sell_amount_before / sell_qty_before - price)

            ELSE 0
        END AS trade_pnl
    FROM ordered
)
SELECT
    ts,
    symbol,
    side,
    qty,
    price,
    buy_qty_before,
    buy_amount_before,
    avg_entry_price_before,
    trade_pnl
FROM calc;

CREATE OR REPLACE VIEW v_today_pnl_summary_ru AS
SELECT
    now() AS "Время",
    round(COALESCE(sum(trade_pnl), 0), 2) AS "P&L за день",
    count(*) AS "Сделок",
    count(DISTINCT symbol) AS "Инструментов"
FROM v_today_trade_pnl_calc;
