DROP VIEW IF EXISTS v_trades_drawdown_curve_grafana CASCADE;
DROP VIEW IF EXISTS v_trades_drawdown_curve_ui CASCADE;

CREATE VIEW v_trades_drawdown_curve_ui AS
WITH equity AS (
  SELECT
    ts,
    "Инструмент",
    "Тикер",
    "Источник",
    "Realized P&L",
    "Equity P&L",
    MAX("Equity P&L") OVER (
      PARTITION BY "Тикер", "Источник"
      ORDER BY ts
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS "Peak Equity P&L"
  FROM v_trades_equity_curve_ui
),
drawdown AS (
  SELECT
    ts,
    "Инструмент",
    "Тикер",
    "Источник",
    "Realized P&L",
    "Equity P&L",
    "Peak Equity P&L",
    ROUND(("Equity P&L" - "Peak Equity P&L")::numeric, 2) AS "Drawdown",
    ROUND(
      CASE
        WHEN "Peak Equity P&L" = 0 THEN 0
        ELSE 100.0 * ("Equity P&L" - "Peak Equity P&L") / ABS("Peak Equity P&L")
      END::numeric,
      2
    ) AS "Drawdown %"
  FROM equity
)
SELECT *
FROM drawdown
ORDER BY ts;

CREATE VIEW v_trades_drawdown_curve_grafana AS
SELECT
  ts AS time,
  "Инструмент",
  "Тикер",
  "Источник",
  "Equity P&L",
  "Peak Equity P&L",
  "Drawdown",
  "Drawdown %"
FROM v_trades_drawdown_curve_ui
ORDER BY time;
