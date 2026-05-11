CREATE OR REPLACE VIEW v_real_portfolio_positions_ui AS
SELECT
    CASE
        WHEN "Тикер" IN ('SU29010RMFS4@MISX', 'SU26243RMFS4@MISX') THEN 'ОФЗ'
        WHEN "Тикер" = 'POSI@MISX' THEN 'Позитив'
        WHEN "Тикер" = 'SGZH@MISX' THEN 'Сегежа'
        ELSE "Название"
    END AS "Инструмент",
    CASE
        WHEN "Количество" < 0 THEN 'Шорт'
        WHEN "Количество" > 0 THEN 'Лонг'
        ELSE 'Нет позиции'
    END AS "Позиция",
    ROUND(ABS("Количество")::numeric, 2) AS "Количество",
    ROUND("Средняя цена"::numeric, 2) AS "Средняя",
    ROUND("Текущая цена"::numeric, 2) AS "Текущая",
    ROUND("Оценка"::numeric, 2) AS "Оценка",
    ROUND("P&L общий"::numeric, 2) AS "P&L",
    ROUND("P&L за день"::numeric, 2) AS "День",
    "Валюта",
    "Обновлено"
FROM v_real_portfolio_positions_ru
WHERE ABS("Количество") > 0
ORDER BY "Оценка" DESC;
