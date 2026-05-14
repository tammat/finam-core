#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE OR REPLACE VIEW grafana_closed_trade_summary AS
SELECT
    symbol,
    COUNT(*) AS trades,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) AS losses,
    SUM(net_pnl) AS net_pnl,
    AVG(net_pnl) AS expectancy,
    SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
        / NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0) AS profit_factor,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::double precision
        / NULLIF(COUNT(*), 0) * 100 AS winrate
FROM closed_trades
GROUP BY symbol
ORDER BY net_pnl DESC;

CREATE OR REPLACE VIEW grafana_closed_trade_equity_curve AS
SELECT
    exit_ts AS time,
    symbol,
    net_pnl,
    SUM(net_pnl) OVER (
        ORDER BY exit_ts, id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_pnl
FROM closed_trades
WHERE exit_ts IS NOT NULL
ORDER BY exit_ts, id;

CREATE OR REPLACE VIEW grafana_closed_trade_daily AS
SELECT
    date_trunc('day', exit_ts) AS time,
    symbol,
    COUNT(*) AS trades,
    SUM(net_pnl) AS net_pnl,
    AVG(net_pnl) AS expectancy,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::double precision
        / NULLIF(COUNT(*), 0) * 100 AS winrate
FROM closed_trades
WHERE exit_ts IS NOT NULL
GROUP BY 1, symbol
ORDER BY 1 DESC, symbol;
SQL

echo "OK: Grafana base closed trade views created"
