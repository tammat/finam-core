DROP VIEW IF EXISTS v_broker_order_snapshot_alerts_grafana CASCADE;

CREATE VIEW v_broker_order_snapshot_alerts_grafana AS
WITH latest AS (
    SELECT DISTINCT ON (order_id)
        *
    FROM broker_order_snapshots
    WHERE order_id IS NOT NULL AND order_id <> ''
    ORDER BY order_id, ts DESC
),
classified AS (
    SELECT
        ts,
        order_id,
        symbol,
        side,
        status,
        qty,
        filled_qty,
        remaining_qty,
        source,
        raw,
        CASE
            WHEN symbol IS NULL OR symbol = '' THEN 'ALERT_EMPTY_SYMBOL'
            WHEN side IS NULL OR side = '' OR side = '0' THEN 'ALERT_INVALID_SIDE'
            WHEN qty = 0 AND status NOT IN ('3', 'ORDER_STATUS_FILLED', 'FILLED', 'EXECUTED') THEN 'ALERT_ZERO_QTY_ACTIVE_STATUS'
            WHEN remaining_qty > 0 THEN 'ALERT_REMAINING_QTY'
            WHEN status IN ('0', '', 'ORDER_STATUS_UNSPECIFIED') THEN 'ALERT_UNKNOWN_STATUS'
            ELSE 'OK'
        END AS alert
    FROM latest
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
    alert AS "Alert",
    source AS "Источник",
    raw AS "Raw"
FROM classified
WHERE alert <> 'OK'
ORDER BY ts DESC;
