DROP VIEW IF EXISTS v_trades_pnl_manual_ui CASCADE;
DROP VIEW IF EXISTS v_trades_pnl_auto_ui CASCADE;
DROP VIEW IF EXISTS v_real_portfolio_pnl_ui CASCADE;
DROP VIEW IF EXISTS v_real_portfolio_positions_ui CASCADE;

CREATE VIEW v_trades_pnl_manual_ui AS
SELECT
  COALESCE(ir.short_name, ir.display_name, t.symbol) AS "Инструмент",
  t.symbol AS "Тикер",
  COALESCE(t.trade_source, 'unknown') AS "Источник",
  ROUND(SUM(CASE WHEN UPPER(t.side) = 'SELL' THEN t.qty * t.price ELSE -t.qty * t.price END)::numeric, 2) AS "Денежный результат",
  ROUND(SUM(COALESCE(t.commission, 0))::numeric, 2) AS "Комиссия",
  COUNT(*) AS "Сделок",
  MAX(COALESCE(t.ts, t.created_at)) AS "Последняя сделка"
FROM trades t
LEFT JOIN instrument_reference ir ON ir.symbol = t.symbol
WHERE LOWER(COALESCE(t.trade_source, 'unknown')) = 'manual'
GROUP BY COALESCE(ir.short_name, ir.display_name, t.symbol), t.symbol, COALESCE(t.trade_source, 'unknown')
ORDER BY "Денежный результат" ASC;

CREATE VIEW v_trades_pnl_auto_ui AS
SELECT
  COALESCE(ir.short_name, ir.display_name, t.symbol) AS "Инструмент",
  t.symbol AS "Тикер",
  COALESCE(t.trade_source, 'unknown') AS "Источник",
  ROUND(SUM(CASE WHEN UPPER(t.side) = 'SELL' THEN t.qty * t.price ELSE -t.qty * t.price END)::numeric, 2) AS "Денежный результат",
  ROUND(SUM(COALESCE(t.commission, 0))::numeric, 2) AS "Комиссия",
  COUNT(*) AS "Сделок",
  MAX(COALESCE(t.ts, t.created_at)) AS "Последняя сделка"
FROM trades t
LEFT JOIN instrument_reference ir ON ir.symbol = t.symbol
WHERE LOWER(COALESCE(t.trade_source, 'unknown')) IN ('robot', 'paper', 'real_api', 'auto')
GROUP BY COALESCE(ir.short_name, ir.display_name, t.symbol), t.symbol, COALESCE(t.trade_source, 'unknown')
ORDER BY "Денежный результат" ASC;
