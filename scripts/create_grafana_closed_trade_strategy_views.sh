#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE OR REPLACE VIEW grafana_closed_trade_by_strategy AS
SELECT
    COALESCE(
        payload->'payload'->'entry_payload'->>'strategy',
        payload->'payload'->'exit_payload'->>'strategy',
        payload->>'strategy',
        'unknown'
    ) AS strategy,
    COUNT(*) AS trades,
    SUM(net_pnl) AS net_pnl,
    AVG(net_pnl) AS expectancy,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::double precision
        / NULLIF(COUNT(*), 0) * 100 AS winrate,
    SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
        / NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0) AS profit_factor
FROM closed_trades
GROUP BY strategy
ORDER BY net_pnl DESC;

CREATE OR REPLACE VIEW grafana_closed_trade_by_horizon AS
SELECT
    COALESCE(
        payload->'payload'->'entry_payload'->>'horizon',
        payload->'payload'->'exit_payload'->>'horizon',
        payload->>'horizon',
        'unknown'
    ) AS horizon,
    COUNT(*) AS trades,
    SUM(net_pnl) AS net_pnl,
    AVG(net_pnl) AS expectancy,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::double precision
        / NULLIF(COUNT(*), 0) * 100 AS winrate,
    SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
        / NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0) AS profit_factor
FROM closed_trades
GROUP BY horizon
ORDER BY net_pnl DESC;

CREATE OR REPLACE VIEW grafana_closed_trade_by_regime AS
SELECT
    COALESCE(
        payload->'payload'->'entry_payload'->>'regime_direction',
        payload->'payload'->'exit_payload'->>'regime_direction',
        payload->>'regime_direction',
        'unknown'
    ) AS regime_direction,
    COUNT(*) AS trades,
    SUM(net_pnl) AS net_pnl,
    AVG(net_pnl) AS expectancy,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::double precision
        / NULLIF(COUNT(*), 0) * 100 AS winrate,
    SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
        / NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0) AS profit_factor
FROM closed_trades
GROUP BY regime_direction
ORDER BY net_pnl DESC;
SQL

echo "OK: strategy/horizon/regime Grafana views created"
