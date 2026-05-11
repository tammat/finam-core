DROP VIEW IF EXISTS v_order_reconciliation_alerts_grafana CASCADE;

CREATE VIEW v_order_reconciliation_alerts_grafana AS
SELECT
    ts AS time,
    to_char(ts AT TIME ZONE 'Europe/Moscow', 'DD-MM-YYYY HH24:MI:SS') AS "Дата",
    id AS "Run ID",
    status AS "Статус",
    acks_count AS "ACK",
    broker_orders_count AS "Broker Orders",
    issues_count AS "Issues",
    CASE
        WHEN issues_count > 0 THEN 'ALERT_RECONCILIATION_ISSUES'
        WHEN status <> 'OK' THEN 'ALERT_RECONCILIATION_STATUS'
        ELSE 'OK'
    END AS "Alert",
    source AS "Источник",
    raw AS "Raw"
FROM order_reconciliation_runs
WHERE issues_count > 0 OR status <> 'OK'
ORDER BY ts DESC;
