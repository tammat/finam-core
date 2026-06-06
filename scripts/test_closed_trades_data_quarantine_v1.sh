#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/materialize_closed_trades_data_quarantine_v1.py

python3 src/scripts/research/materialize_closed_trades_data_quarantine_v1.py | \
  tee /tmp/closed_trades_data_quarantine_v1.log

grep -q "CLOSED TRADES DATA QUARANTINE V1" /tmp/closed_trades_data_quarantine_v1.log
grep -q "delete_rows=0" /tmp/closed_trades_data_quarantine_v1.log
grep -q "mutate_closed_trades=0" /tmp/closed_trades_data_quarantine_v1.log
grep -q "TOTAL_CLOSED_TRADES=" /tmp/closed_trades_data_quarantine_v1.log
grep -q "QUARANTINED_TRADES=" /tmp/closed_trades_data_quarantine_v1.log
grep -q "ROWS_WRITTEN=" /tmp/closed_trades_data_quarantine_v1.log
grep -q "VERDICT=OK" /tmp/closed_trades_data_quarantine_v1.log

psql "$DATABASE_URL" -c "
select
  severity,
  count(*) as rows
from research_closed_trades_quarantine
group by severity
order by severity;
"

psql "$DATABASE_URL" -c "
select
  trade_id,
  symbol,
  severity,
  net_pnl,
  exit_price,
  quarantine_reason
from research_closed_trades_quarantine
order by net_pnl asc
limit 20;
"

echo CLOSED_TRADES_DATA_QUARANTINE_V1_OK
