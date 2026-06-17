#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== USDRUBF V3 MAX DURATION GUARD V1 ==="
echo "mode=diagnostic"
echo "runtime_allow=0"
echo "execution_enabled=0"

psql "$DATABASE_URL" -c "
select
    count(*) as chains,
    count(*) filter (where exit_ts - entry_ts <= interval '120 minutes') as valid_intraday_chains,
    count(*) filter (where exit_ts - entry_ts > interval '120 minutes') as contaminated_chains,
    round(sum(net_pnl) filter (where exit_ts - entry_ts <= interval '120 minutes'),6) as valid_pnl,
    round(sum(net_pnl) filter (where exit_ts - entry_ts > interval '120 minutes'),6) as contaminated_pnl
from closed_trade_chains_v3
where symbol='USDRUBF@RTSX'
  and strategy='USD_INTRADAY_REGIME';
"

contaminated=$(psql "$DATABASE_URL" -At -c "
select count(*)
from closed_trade_chains_v3
where symbol='USDRUBF@RTSX'
  and strategy='USD_INTRADAY_REGIME'
  and exit_ts - entry_ts > interval '120 minutes';
")

echo "contaminated_usdrubf_chains=${contaminated}"

if [ "$contaminated" = "0" ]; then
  echo "FAIL: expected contaminated USDRUBF chain was not detected"
  exit 1
fi

echo "USDRUBF_V3_MAX_DURATION_GUARD_V1_OK"
