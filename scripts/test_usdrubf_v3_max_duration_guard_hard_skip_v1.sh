#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

python3 -m py_compile src/scripts/research/build_fill_pairing_engine_v3.py

echo "=== USDRUBF V3 MAX DURATION HARD SKIP V1 ==="
echo "mode=research_only"
echo "runtime_allow=0"
echo "execution_enabled=0"

bash scripts/test_fill_pairing_engine_v3_skip_burst.sh \
  | tee /tmp/usdrubf_v3_max_duration_hard_skip_v1.log

grep -q "FILL_PAIRING_V3_SKIP_CHAIN" /tmp/usdrubf_v3_max_duration_hard_skip_v1.log
grep -q "usd_intraday_duration_exceeded" /tmp/usdrubf_v3_max_duration_hard_skip_v1.log

contaminated=$(psql "$DATABASE_URL" -At -c "
select count(*)
from closed_trade_chains_v3
where symbol='USDRUBF@RTSX'
  and strategy='USD_INTRADAY_REGIME'
  and exit_ts - entry_ts > interval '120 minutes';
")

valid_chains=$(psql "$DATABASE_URL" -At -c "
select count(*)
from closed_trade_chains_v3
where symbol='USDRUBF@RTSX'
  and strategy='USD_INTRADAY_REGIME';
")

valid_pnl=$(psql "$DATABASE_URL" -At -c "
select round(coalesce(sum(net_pnl),0),6)
from closed_trade_chains_v3
where symbol='USDRUBF@RTSX'
  and strategy='USD_INTRADAY_REGIME';
")

echo "contaminated_usdrubf_chains=${contaminated}"
echo "valid_usdrubf_chains=${valid_chains}"
echo "valid_usdrubf_pnl=${valid_pnl}"

if [ "${contaminated}" != "0" ]; then
  echo "FAIL: contaminated USDRUBF chains still present"
  exit 1
fi

if [ "${valid_chains}" != "7" ]; then
  echo "FAIL: expected 7 valid USDRUBF chains after hard skip"
  exit 1
fi

echo "USDRUBF_V3_MAX_DURATION_GUARD_HARD_SKIP_V1_OK"
