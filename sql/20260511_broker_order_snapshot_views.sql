DROP VIEW IF EXISTS v_broker_order_snapshots_active_grafana CASCADE;
DROP VIEW IF EXISTS v_broker_order_snapshots_recent_grafana CASCADE;

CREATE VIEW v_broker_order_snapshots_recent_grafana AS
SELECT
    ts AS time,
    to_char(ts AT TIME ZONE 'Europe/Moscow', 'DD-MM-YYYY HH24:MI:SS') AS "Дата",
    order_id AS "Order ID",
    symbol AS "Тикер",
    side AS "Сторона",
    status AS "Статус",
    ROUND(qty::numeric, 4) AS "Qty",
    ROUND(filled_qty::numeric, 4) AS "Filled",
    ROUND(remaining_qty::numeric, 4) AS "Remaining",
    source AS "Источник",
    raw AS "Raw"
FROM broker_order_snapshots
ORDER BY ts DESC;

CREATE VIEW v_broker_order_snapshots_active_grafana AS
WITH latest AS (
    SELECT DISTINCT ON (order_id)
        *
    FROM broker_order_snapshots
    WHERE order_id IS NOT NULL AND order_id <> ''
    ORDER BY order_id, ts DESC
)
SELECT
    ts AS time,
    to_char(ts AT TIME ZONE 'Europe/Moscow', 'DD-MM-YYYY HH24:MI:SS') AS "Дата",
    order_id AS "Order ID",
    symbol AS "Тикер",
    side AS "Сторона",
    status AS "Статус",
    ROUND(qty::numeric, 4) AS "Qty",
    ROUND(filled_qty::numeric, 4) AS "Filled",
    ROUND(remaining_qty::numeric, 4) AS "Remaining",
    source AS "Источник"
FROM latest
WHERE status NOT IN ('3', 'ORDER_STATUS_FILLED', 'FILLED', 'EXECUTED')
ORDER BY ts DESC;
