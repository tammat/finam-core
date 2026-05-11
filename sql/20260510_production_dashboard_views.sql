CREATE OR REPLACE VIEW v_production_health AS
SELECT
    now() AS checked_at,
    (SELECT COALESCE(max(id), 0) FROM event_store) AS latest_event_id,
    (
        SELECT COALESCE(last_event_id, 0)
        FROM projection_checkpoints
        WHERE name = 'projection_worker'
    ) AS projection_checkpoint_id,
    (
        (SELECT COALESCE(max(id), 0) FROM event_store)
        -
        COALESCE((
            SELECT last_event_id
            FROM projection_checkpoints
            WHERE name = 'projection_worker'
        ), 0)
    ) AS projection_lag,
    (
        SELECT count(*)
        FROM event_dead_letters
        WHERE resolved = false
    ) AS dlq_unresolved,
    (
        SELECT count(*)
        FROM order_projection
    ) AS orders_count,
    (
        SELECT count(*)
        FROM position_projection
    ) AS positions_count,
    (
        SELECT state
        FROM portfolio_projection
        WHERE id = 'GLOBAL'
    ) AS portfolio_state;

CREATE OR REPLACE VIEW v_orders_dashboard AS
SELECT
    order_id,
    state->>'symbol' AS symbol,
    state->>'side' AS side,
    state->>'status' AS status,
    state->>'reason' AS reason,
    updated_at
FROM order_projection
ORDER BY updated_at DESC;

CREATE OR REPLACE VIEW v_positions_dashboard AS
SELECT
    symbol,
    (state->>'qty')::numeric AS qty,
    (state->>'avg_price')::numeric AS avg_price,
    (state->>'realized_pnl')::numeric AS realized_pnl,
    updated_at
FROM position_projection
ORDER BY symbol;

CREATE OR REPLACE VIEW v_dlq_dashboard AS
SELECT
    id,
    event_id,
    event_type,
    worker_name,
    error_type,
    error_message,
    resolved,
    created_at
FROM event_dead_letters
ORDER BY id DESC;

CREATE OR REPLACE VIEW v_positions_dashboard_ru AS
SELECT
    p.symbol,
    COALESCE(i.display_name, p.symbol) AS "Название",
    p.symbol AS "Тикер",
    COALESCE(i.asset_class, 'unknown') AS "Класс",
    COALESCE(i.source, 'unknown') AS "Источник",
    (p.state->>'qty')::numeric AS "Количество",
    (p.state->>'avg_price')::numeric AS "Средняя цена",
    (p.state->>'realized_pnl')::numeric AS "Реализованный PnL",
    p.updated_at AS "Обновлено"
FROM position_projection p
LEFT JOIN instrument_reference i ON i.symbol = p.symbol
ORDER BY "Название";

CREATE OR REPLACE VIEW v_orders_dashboard_ru AS
SELECT
    o.order_id AS "ID заявки",
    COALESCE(i.display_name, o.state->>'symbol') AS "Название",
    o.state->>'symbol' AS "Тикер",
    CASE o.state->>'side'
        WHEN 'BUY' THEN 'Покупка'
        WHEN 'SELL' THEN 'Продажа'
        ELSE COALESCE(o.state->>'side', '')
    END AS "Сторона",
    CASE o.state->>'status'
        WHEN 'CREATED' THEN 'Создана'
        WHEN 'SENT' THEN 'Отправлена'
        WHEN 'FILLED' THEN 'Исполнена'
        WHEN 'REJECTED' THEN 'Отклонена'
        WHEN 'CANCELLED' THEN 'Отменена'
        ELSE COALESCE(o.state->>'status', '')
    END AS "Статус",
    COALESCE(o.state->>'reason', '') AS "Причина",
    o.updated_at AS "Обновлено"
FROM order_projection o
LEFT JOIN instrument_reference i ON i.symbol = o.state->>'symbol'
ORDER BY o.updated_at DESC;

CREATE OR REPLACE VIEW v_portfolio_visualization_ru AS
SELECT
    COALESCE(i.display_name, p.symbol) AS "Название",
    p.symbol AS "Тикер",
    ABS((p.state->>'qty')::numeric) AS "Количество",
    ABS((p.state->>'qty')::numeric * (p.state->>'avg_price')::numeric) AS "Оценка позиции",
    (p.state->>'realized_pnl')::numeric AS "Реализованный PnL"
FROM position_projection p
LEFT JOIN instrument_reference i ON i.symbol = p.symbol
WHERE ABS((p.state->>'qty')::numeric) > 0
ORDER BY "Оценка позиции" DESC;
