DROP VIEW IF EXISTS v_trades_drawdown_summary_grafana CASCADE;

CREATE VIEW v_trades_drawdown_summary_grafana AS
SELECT
  "Инструмент",
  "Тикер",
  "Источник",
  ROUND(MIN("Drawdown")::numeric, 2) AS "Max Drawdown",
  ROUND(MIN("Drawdown %")::numeric, 2) AS "Max Drawdown %",
  ROUND(MAX("Equity P&L")::numeric, 2) AS "Peak Equity P&L",
  ROUND((ARRAY_AGG("Equity P&L" ORDER BY time DESC))[1]::numeric, 2) AS "Current Equity P&L",
  COUNT(*) AS "Точек кривой"
FROM v_trades_drawdown_curve_grafana
GROUP BY "Инструмент", "Тикер", "Источник"
ORDER BY "Max Drawdown" ASC;
