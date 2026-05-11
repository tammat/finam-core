DROP VIEW IF EXISTS v_trades_pnl_paired_grafana CASCADE;
DROP VIEW IF EXISTS v_trades_pnl_paired_ui CASCADE;

CREATE VIEW v_trades_pnl_paired_ui AS
WITH buys AS (
  SELECT
    t.*,
    ROW_NUMBER() OVER (
      PARTITION BY t.symbol, COALESCE(t.trade_source, 'unknown')
      ORDER BY COALESCE(t.ts, t.created_at), t.id
    ) AS pair_no
  FROM trades t
  WHERE UPPER(t.side) = 'BUY'
),
sells AS (
  SELECT
    t.*,
    ROW_NUMBER() OVER (
      PARTITION BY t.symbol, COALESCE(t.trade_source, 'unknown')
      ORDER BY COALESCE(t.ts, t.created_at), t.id
    ) AS pair_no
  FROM trades t
  WHERE UPPER(t.side) = 'SELL'
),
paired AS (
  SELECT
    COALESCE(ir.short_name, ir.display_name, b.symbol) AS instrument_name,
    b.symbol,
    COALESCE(b.trade_source, 'unknown') AS trade_source,
    b.pair_no,
    b.qty AS buy_qty,
    b.price AS buy_price,
    COALESCE(b.commission, 0) AS buy_commission,
    COALESCE(b.ts, b.created_at) AS buy_ts,
    s.qty AS sell_qty,
    s.price AS sell_price,
    COALESCE(s.commission, 0) AS sell_commission,
    COALESCE(s.ts, s.created_at) AS sell_ts,
    LEAST(ABS(b.qty), ABS(s.qty)) AS matched_qty
  FROM buys b
  JOIN sells s
    ON s.symbol = b.symbol
   AND COALESCE(s.trade_source, 'unknown') = COALESCE(b.trade_source, 'unknown')
   AND s.pair_no = b.pair_no
  LEFT JOIN instrument_reference ir
    ON ir.symbol = b.symbol
)
SELECT
  instrument_name AS "Инструмент",
  symbol AS "Тикер",
  trade_source AS "Источник",
  pair_no AS "Пара",
  CASE
    WHEN buy_ts <= sell_ts THEN 'LONG'
    ELSE 'SHORT'
  END AS "Тип",
  ROUND(matched_qty::numeric, 4) AS "Количество",
  ROUND(buy_price::numeric, 4) AS "Цена покупки",
  ROUND(sell_price::numeric, 4) AS "Цена продажи",
  ROUND(((sell_price - buy_price) * matched_qty - buy_commission - sell_commission)::numeric, 2) AS "Realized P&L",
  ROUND((buy_commission + sell_commission)::numeric, 2) AS "Комиссия",
  buy_ts AS "Открытие",
  sell_ts AS "Закрытие"
FROM paired
ORDER BY GREATEST(buy_ts, sell_ts) DESC;

CREATE VIEW v_trades_pnl_paired_grafana AS
SELECT
  to_char("Закрытие" AT TIME ZONE 'Europe/Moscow', 'DD-MM-YYYY HH24:MI') AS "Дата закрытия",
  "Инструмент",
  "Тикер",
  "Источник",
  "Тип",
  "Количество",
  "Цена покупки",
  "Цена продажи",
  "Realized P&L",
  "Комиссия"
FROM v_trades_pnl_paired_ui
ORDER BY "Закрытие" DESC;
