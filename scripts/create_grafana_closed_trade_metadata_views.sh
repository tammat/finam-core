#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE OR REPLACE VIEW grafana_closed_trade_execution_type AS
SELECT
    COALESCE(
        payload->'payload'->'entry_payload'->>'execution_type',
        payload->'payload'->'exit_payload'->>'execution_type',
        'unknown'
    ) AS execution_type,
    COUNT(*) AS trades,
    SUM(net_pnl) AS net_pnl,
    AVG(net_pnl) AS expectancy,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::double precision
        / NULLIF(COUNT(*), 0) * 100 AS winrate
FROM closed_trades
GROUP BY execution_type
ORDER BY net_pnl DESC;

CREATE OR REPLACE VIEW grafana_closed_trade_paper_only AS
SELECT
    COALESCE(
        payload->'payload'->'entry_payload'->>'paper_only',
        payload->'payload'->'exit_payload'->>'paper_only',
        'unknown'
    ) AS paper_only,
    COUNT(*) AS trades,
    SUM(net_pnl) AS net_pnl,
    AVG(net_pnl) AS expectancy,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::double precision
        / NULLIF(COUNT(*), 0) * 100 AS winrate
FROM closed_trades
GROUP BY paper_only
ORDER BY net_pnl DESC;
SQL

echo "OK: closed trade metadata Grafana views created"
