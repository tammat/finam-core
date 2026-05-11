DROP VIEW IF EXISTS v_order_reconciliation_issues_grafana CASCADE;
DROP VIEW IF EXISTS v_order_reconciliation_runs_grafana CASCADE;

CREATE VIEW v_order_reconciliation_runs_grafana AS
SELECT
    ts AS time,
    to_char(ts AT TIME ZONE 'Europe/Moscow', 'DD-MM-YYYY HH24:MI:SS') AS "Дата",
    id AS "Run ID",
    acks_count AS "ACK",
    broker_orders_count AS "Broker Orders",
    issues_count AS "Issues",
    status AS "Статус",
    source AS "Источник",
    raw AS "Raw"
FROM order_reconciliation_runs
ORDER BY ts DESC;

CREATE VIEW v_order_reconciliation_issues_grafana AS
SELECT
    i.ts AS time,
    to_char(i.ts AT TIME ZONE 'Europe/Moscow', 'DD-MM-YYYY HH24:MI:SS') AS "Дата",
    i.run_id AS "Run ID",
    i.order_id AS "Order ID",
    i.symbol AS "Тикер",
    i.issue_type AS "Тип проблемы",
    i.reason AS "Причина",
    r.status AS "Статус сверки",
    r.acks_count AS "ACK",
    r.broker_orders_count AS "Broker Orders"
FROM order_reconciliation_issues i
JOIN order_reconciliation_runs r
  ON r.id = i.run_id
ORDER BY i.ts DESC;
