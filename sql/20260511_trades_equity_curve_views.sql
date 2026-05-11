DROP VIEW IF EXISTS v_trades_equity_curve_grafana CASCADE;
DROP VIEW IF EXISTS v_trades_equity_curve_ui CASCADE;

CREATE VIEW v_trades_equity_curve_ui AS
SELECT
  "Закрытие" AS ts,
  "Инструмент",
  "Тикер",
  "Источник",
  "Realized P&L",
  ROUND(SUM("Realized P&L") OVER (PARTITION BY "Тикер", "Источник" ORDER BY "Закрытие")::numeric, 2) AS "Equity P&L"
FROM v_trades_pnl_paired_ui
ORDER BY ts;

CREATE VIEW v_trades_equity_curve_grafana AS
SELECT
  ts AS time,
  "Инструмент",
  "Тикер",
  "Источник",
  "Realized P&L",
  "Equity P&L"
FROM v_trades_equity_curve_ui
ORDER BY time;
