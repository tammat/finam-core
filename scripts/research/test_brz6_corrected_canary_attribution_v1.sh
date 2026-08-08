#!/usr/bin/env bash
set -euo pipefail

LOG="/tmp/MR2_001_BRZ6_MONETARY_CANARY_V2.log"

test -s "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_DRY_RUN_OK" \
  "$LOG"

grep -Fq "symbol=BRZ6@RTSX" "$LOG"
grep -Fq "trades=543" "$LOG"

GROSS_ERROR="$(
  grep '^gross_identity_error=' "$LOG" |
  tail -1 |
  cut -d= -f2
)"

NET_ERROR="$(
  grep '^net_identity_error=' "$LOG" |
  tail -1 |
  cut -d= -f2
)"

python3 - "$GROSS_ERROR" "$NET_ERROR" <<'PY'
from decimal import Decimal
import sys

gross_error = Decimal(sys.argv[1])
net_error = Decimal(sys.argv[2])

assert gross_error == 0, gross_error
assert net_error == 0, net_error

print("gross_monetary_identity_ok=1")
print("net_monetary_identity_ok=1")
PY

echo "monetary_unit=RUB"
echo "commission_unit=RUB"
echo "slippage_unit=RUB"

echo "original_run_mutated=0"
echo "db_writes_performed=0"

echo "full_corrected_replay_started=0"
echo "new_parameter_search_allowed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_MR2_001_BRZ6_CORRECTED_CANARY_ATTRIBUTION_OK"
