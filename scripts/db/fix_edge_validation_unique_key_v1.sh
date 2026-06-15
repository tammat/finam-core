#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"

sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
alter table analytics_edge_validation_v1
drop constraint if exists analytics_edge_validation_v1_symbol_uq;

alter table analytics_edge_validation_v1
add constraint analytics_edge_validation_v1_trade_date_symbol_strategy_tim_key
unique (trade_date, symbol, strategy, timeframe);
SQL

echo "EDGE_VALIDATION_UNIQUE_KEY_FIX_OK"
