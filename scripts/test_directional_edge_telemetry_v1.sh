#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/log_directional_edge_telemetry.py \
  src/finam_core/analytics/directional_edge_guard.py

grep -q "CREATE TABLE IF NOT EXISTS directional_edge_telemetry" \
  sql/create_directional_edge_telemetry.sql

grep -q "advisory_status" \
  sql/create_directional_edge_telemetry.sql

grep -q "guard_mode" \
  sql/create_directional_edge_telemetry.sql

python src/scripts/log_directional_edge_telemetry.py \
  --symbol BRN6@RTSX \
  --continuous-symbol BR_CONT \
  --strategy BR_CONSERVATIVE_BREAKOUT \
  --timeframe M5 \
  --side SELL \
  --regime-direction trend_down \
  --guard-status favorable

python src/scripts/log_directional_edge_telemetry.py \
  --symbol BRN6@RTSX \
  --continuous-symbol BR_CONT \
  --strategy BR_CONSERVATIVE_BREAKOUT \
  --timeframe M5 \
  --side BUY \
  --regime-direction trend_up \
  --guard-status unfavorable

psql "$DATABASE_URL" -c "
select
  regime_direction,
  advisory_status,
  advisory_reason,
  count(*) rows
from directional_edge_telemetry
group by regime_direction, advisory_status, advisory_reason
order by rows desc;
"

echo "DIRECTIONAL_EDGE_TELEMETRY_V1_COMPILE_OK"
