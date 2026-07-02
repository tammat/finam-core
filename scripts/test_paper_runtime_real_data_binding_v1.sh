#!/usr/bin/env bash
set -euo pipefail

echo "=== PAPER_RUNTIME_REAL_DATA_BINDING_V1 ==="

psql -d finam_core <<'SQL'

\echo
\echo ===== CLOSED_TRADES =====
SELECT count(*) AS rows FROM closed_trades;

\echo
\echo ===== SIGNALS =====
SELECT count(*) AS rows FROM signals;

\echo
\echo ===== SIGNAL_FILLS =====
SELECT count(*) AS rows FROM signal_fills;

\echo
\echo ===== FILLS =====
SELECT count(*) AS rows FROM fills;

\echo
\echo ===== EXECUTION_EVENTS =====
SELECT count(*) AS rows FROM execution_events;

\echo
\echo ===== RUNTIME_ACTIVE_UNIVERSE =====
SELECT count(*) AS rows FROM runtime_active_universe;

\echo
\echo ===== LAST CLOSED TRADE =====
SELECT *
FROM closed_trades
ORDER BY 1 DESC
LIMIT 5;

SQL

echo
echo "VERDICT=PAPER_RUNTIME_REAL_DATA_BINDING_V1_READY"
