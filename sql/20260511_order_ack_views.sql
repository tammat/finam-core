DROP VIEW IF EXISTS v_order_acks_reconciliation_grafana CASCADE;
DROP VIEW IF EXISTS v_order_acks_recent_grafana CASCADE;

CREATE VIEW v_order_acks_recent_grafana AS
SELECT
    ts AS time,
    to_char(ts AT TIME ZONE 'Europe/Moscow', 'DD-MM-YYYY HH24:MI:SS') AS "Дата",
    symbol AS "Тикер",
    side AS "Сторона",
    ROUND(qty::numeric, 4) AS "Количество",
    COALESCE(order_id, '') AS "Order ID",
    status AS "Статус ACK",
    COALESCE(reason, '') AS "Причина",
    source AS "Источник",
    raw AS "Raw"
FROM order_acks
ORDER BY ts DESC;

CREATE VIEW v_order_acks_reconciliation_grafana AS
SELECT
    ts AS time,
    to_char(ts AT TIME ZONE 'Europe/Moscow', 'DD-MM-YYYY HH24:MI:SS') AS "Дата",
    symbol AS "Тикер",
    side AS "Сторона",
    ROUND(qty::numeric, 4) AS "Количество",
    COALESCE(order_id, '') AS "Order ID",
    status AS "Статус ACK",
    COALESCE(reason, '') AS "Причина",
    source AS "Источник",
    CASE
        WHEN order_id IS NULL OR order_id = '' THEN 'NO_ORDER_ID'
        WHEN reason IS NOT NULL AND reason <> '' THEN 'ACK_WITH_REASON'
        WHEN UPPER(status) IN ('ACCEPTED', 'PLACED', 'NEW', 'ORDER_STATUS_NEW') THEN 'ACK_OK'
        ELSE 'ACK_CHECK_REQUIRED'
    END AS "Сверка ACK"
FROM order_acks
ORDER BY ts DESC;
