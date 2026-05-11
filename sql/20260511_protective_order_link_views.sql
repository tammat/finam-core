DROP VIEW IF EXISTS v_protective_order_unprotected_entries_grafana CASCADE;
DROP VIEW IF EXISTS v_protective_order_links_grafana CASCADE;

CREATE VIEW v_protective_order_links_grafana AS
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
    CASE
        WHEN COALESCE(stop_order_id, '') <> '' OR COALESCE(take_order_id, '') <> '' THEN 'PROTECTED'
        ELSE 'UNPROTECTED'
    END AS "Защита",
    source AS "Источник",
    raw AS "Raw"
FROM protective_order_links
ORDER BY ts DESC;

CREATE VIEW v_protective_order_unprotected_entries_grafana AS
SELECT
    ts AS time,
    to_char(ts AT TIME ZONE 'Europe/Moscow', 'DD-MM-YYYY HH24:MI:SS') AS "Дата",
    symbol AS "Тикер",
    side AS "Сторона",
    ROUND(qty::numeric, 4) AS "Qty",
    entry_order_id AS "Entry Order ID",
    status AS "Статус",
    'MISSING_STOP_TAKE_LINK' AS "Alert",
    source AS "Источник",
    raw AS "Raw"
FROM protective_order_links
WHERE status = 'OPEN'
  AND COALESCE(stop_order_id, '') = ''
  AND COALESCE(take_order_id, '') = ''
ORDER BY ts DESC;
