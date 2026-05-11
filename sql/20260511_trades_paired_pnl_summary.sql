DROP VIEW IF EXISTS v_trades_pnl_paired_summary_grafana CASCADE;

CREATE VIEW v_trades_pnl_paired_summary_grafana AS
SELECT
  "Инструмент",
  "Тикер",
  "Источник",
  COUNT(*) AS "Закрытых сделок",
  ROUND(SUM("Realized P&L")::numeric, 2) AS "Realized P&L",
  ROUND(AVG("Realized P&L")::numeric, 2) AS "Средний P&L",
  ROUND(SUM(CASE WHEN "Realized P&L" > 0 THEN 1 ELSE 0 END)::numeric, 0) AS "Прибыльных",
  ROUND(SUM(CASE WHEN "Realized P&L" < 0 THEN 1 ELSE 0 END)::numeric, 0) AS "Убыточных",
  ROUND(
    100.0 * SUM(CASE WHEN "Realized P&L" > 0 THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0),
    2
  ) AS "Winrate %",
  ROUND(MIN("Realized P&L")::numeric, 2) AS "Худшая сделка",
  ROUND(MAX("Realized P&L")::numeric, 2) AS "Лучшая сделка"
FROM v_trades_pnl_paired_ui
GROUP BY "Инструмент", "Тикер", "Источник"
ORDER BY "Realized P&L" DESC;
