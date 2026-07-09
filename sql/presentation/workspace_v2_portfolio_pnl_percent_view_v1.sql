CREATE OR REPLACE VIEW presentation.v_workspace_v2_portfolio_positions_ru AS
SELECT
    "Название",
    "Тикер",
    "Количество",
    "Средняя цена",
    "Текущая цена",
    "Оценка",
    "P&L общий",
    CASE
        WHEN "Средняя цена" IS NULL
          OR "Количество" IS NULL
          OR ("Средняя цена" * "Количество") = 0
        THEN NULL
        ELSE ROUND(("P&L общий" / NULLIF(("Средняя цена" * "Количество"), 0)) * 100, 2)
    END AS "P&L %",
    "P&L за день",
    "Валюта",
    "Обновлено"
FROM public.v_real_portfolio_positions_ru_base;
