DROP VIEW IF EXISTS v_protective_order_recovery_alerts_grafana CASCADE;

CREATE VIEW v_protective_order_recovery_alerts_grafana AS
SELECT
    ts AS time,
    to_char(ts AT TIME ZONE 'Europe/Moscow', 'DD-MM-YYYY HH24:MI:SS') AS "Дата",
    symbol AS "Тикер",
    side AS "Сторона",
    ROUND(qty::numeric, 4) AS "Qty",
    entry_order_id AS "Entry Order ID",
    COALESCE(stop_order_id, '') AS "Stop Order ID",
    COALESCE(take_order_id, '') AS "Take Order ID",
    status AS "Статус",
    'PROTECTIVE_LINK_UNPROTECTED_ENTRY' AS "Issue Type",
    'open_entry_has_no_stop_or_take_link' AS "Reason",
    'RECOVERY_REQUIRED' AS "Alert",
    source AS "Источник",
    raw AS "Raw"
FROM protective_order_links
WHERE status = 'OPEN'
  AND COALESCE(stop_order_id, '') = ''
  AND COALESCE(take_order_id, '') = ''
ORDER BY ts DESC;
