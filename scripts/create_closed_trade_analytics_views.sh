#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'

-- =========================================================
-- Hour-of-day analytics
-- =========================================================

CREATE OR REPLACE VIEW grafana_closed_trade_hourly AS
SELECT
    EXTRACT(HOUR FROM exit_ts) AS hour,
    symbol,

    COUNT(*) AS trades,

    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) AS losses,

    SUM(net_pnl) AS net_pnl,
    AVG(net_pnl) AS expectancy,

    SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
        / NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0)
        AS profit_factor,

    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::double precision
        / NULLIF(COUNT(*), 0) * 100
        AS winrate

FROM closed_trades
WHERE exit_ts IS NOT NULL
GROUP BY hour, symbol
ORDER BY hour, symbol;


-- =========================================================
-- Weekday analytics
-- =========================================================

CREATE OR REPLACE VIEW grafana_closed_trade_weekday AS
SELECT
    EXTRACT(ISODOW FROM exit_ts) AS weekday,
    symbol,

    COUNT(*) AS trades,
    SUM(net_pnl) AS net_pnl,
    AVG(net_pnl) AS expectancy,

    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::double precision
        / NULLIF(COUNT(*), 0) * 100
        AS winrate

FROM closed_trades
WHERE exit_ts IS NOT NULL
GROUP BY weekday, symbol
ORDER BY weekday, symbol;


-- =========================================================
-- Time heatmap
-- =========================================================

CREATE OR REPLACE VIEW grafana_closed_trade_heatmap AS
SELECT
    EXTRACT(ISODOW FROM exit_ts) AS weekday,
    EXTRACT(HOUR FROM exit_ts) AS hour,
    symbol,

    COUNT(*) AS trades,
    SUM(net_pnl) AS net_pnl,
    AVG(net_pnl) AS expectancy,

    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::double precision
        / NULLIF(COUNT(*), 0) * 100
        AS winrate

FROM closed_trades
WHERE exit_ts IS NOT NULL
GROUP BY weekday, hour, symbol
ORDER BY weekday, hour, symbol;

SQL

echo "OK: analytics views created"
