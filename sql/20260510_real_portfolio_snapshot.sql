CREATE TABLE IF NOT EXISTS real_portfolio_positions (
    symbol TEXT PRIMARY KEY,
    qty NUMERIC NOT NULL DEFAULT 0,
    avg_price NUMERIC NOT NULL DEFAULT 0,
    current_price NUMERIC NOT NULL DEFAULT 0,
    market_value NUMERIC NOT NULL DEFAULT 0,
    pnl NUMERIC NOT NULL DEFAULT 0,
    pnl_day NUMERIC NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'RUB',
    source TEXT NOT NULL DEFAULT 'manual_or_finam',
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE VIEW v_real_portfolio_positions_ru AS
SELECT
    COALESCE(i.short_name, i.display_name, p.symbol) AS "Название",
    p.symbol AS "Тикер",
    p.qty AS "Количество",
    p.avg_price AS "Средняя цена",
    p.current_price AS "Текущая цена",
    p.market_value AS "Оценка",
    p.pnl AS "P&L общий",
    p.pnl_day AS "P&L за день",
    p.currency AS "Валюта",
    p.updated_at AS "Обновлено"
FROM real_portfolio_positions p
LEFT JOIN instrument_reference i ON i.symbol = p.symbol
ORDER BY p.market_value DESC;

CREATE OR REPLACE VIEW v_real_portfolio_summary_ru AS
SELECT
    now() AS "Время",
    COALESCE(SUM(market_value), 0) AS "Стоимость портфеля",
    COALESCE(SUM(pnl), 0) AS "P&L общий",
    COALESCE(SUM(pnl_day), 0) AS "P&L за день",
    COUNT(*) AS "Позиций"
FROM real_portfolio_positions;
