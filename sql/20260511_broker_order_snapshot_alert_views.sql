DROP VIEW IF EXISTS v_broker_order_snapshot_alerts_grafana CASCADE;

CREATE VIEW v_broker_order_snapshot_alerts_grafana AS
WITH status_map AS (
    SELECT *
    FROM (VALUES
        ('3',  'ORDER_STATUS_FILLED',       true),
        ('5',  'ORDER_STATUS_CANCELED',     true),
        ('21', 'ORDER_STATUS_WATCHING',     false),
        ('22', 'ORDER_STATUS_EXECUTED',     true),
        ('23', 'ORDER_STATUS_DISABLED',     true),
        ('28', 'ORDER_STATUS_SL_EXECUTED',  true),
        ('31', 'ORDER_STATUS_TP_EXECUTED',  true)
    ) AS m(status_code, status_name, terminal)
),
latest AS (
    SELECT DISTINCT ON (order_id)
        s.*,
        COALESCE(m.status_name, s.status) AS normalized_status,
        COALESCE(m.terminal, false) AS terminal_status
    FROM broker_order_snapshots s
    LEFT JOIN status_map m
      ON m.status_code = s.status
    WHERE s.order_id IS NOT NULL AND s.order_id <> ''
    ORDER BY s.order_id, s.ts DESC
),
classified AS (
    SELECT
        ts,
        order_id,
        symbol,
        side,
        status,
        normalized_status,
        terminal_status,
        qty,
        filled_qty,
        remaining_qty,
        source,
        raw,
        CASE
            WHEN terminal_status THEN 'OK'
            WHEN status = '21' THEN 'OK'
            WHEN symbol IS NULL OR symbol = '' THEN 'ALERT_EMPTY_SYMBOL'
            WHEN side IS NULL OR side = '' OR side = '0' THEN 'ALERT_INVALID_SIDE'
            WHEN qty = 0 AND NOT terminal_status THEN 'ALERT_ZERO_QTY_ACTIVE_STATUS'
            WHEN remaining_qty > 0 AND NOT terminal_status THEN 'ALERT_REMAINING_QTY'
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
    normalized_status AS "Статус Finam",
    terminal_status AS "Терминальный статус",
    ROUND(qty::numeric, 4) AS "Qty",
    ROUND(filled_qty::numeric, 4) AS "Filled",
    ROUND(remaining_qty::numeric, 4) AS "Remaining",
    alert AS "Alert",
    source AS "Источник",
    raw AS "Raw"
FROM classified
WHERE alert <> 'OK'
ORDER BY ts DESC;
