DROP VIEW IF EXISTS v_real_portfolio_pnl_ui CASCADE;
DROP VIEW IF EXISTS v_real_portfolio_positions_ui CASCADE;

CREATE VIEW v_real_portfolio_positions_ui AS
SELECT
  "Название" AS "Инструмент",
  CASE WHEN "Количество" < 0 THEN 'Шорт' ELSE 'Лонг' END AS "Позиция",
  ROUND(ABS("Количество")::numeric, 2) AS "Количество",
  ROUND("Средняя цена"::numeric, 2) AS "Средняя",
  ROUND("Текущая цена"::numeric, 2) AS "Текущая",
  ROUND("Оценка"::numeric, 2) AS "Оценка",
  "Валюта",
  "Обновлено"
FROM v_real_portfolio_positions_ru
WHERE ABS("Количество") > 0
ORDER BY "Оценка" DESC;

CREATE VIEW v_real_portfolio_pnl_ui AS
SELECT
  "Название" AS "Инструмент",
  CASE WHEN "Количество" < 0 THEN 'Шорт' ELSE 'Лонг' END AS "Позиция",
  ROUND("P&L общий"::numeric, 2) AS "P&L общий",
  ROUND("P&L за день"::numeric, 2) AS "P&L за день",
  ROUND("Оценка"::numeric, 2) AS "Оценка",
  "Валюта",
  "Обновлено"
FROM v_real_portfolio_positions_ru
WHERE ABS("Количество") > 0
ORDER BY "P&L общий" ASC;
