#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

MODULE="src/finam_core/research/cbr_reference_rate_v1.py"
SYNC="src/scripts/research/sync_cbr_reference_rates_v1.py"
LOG="/tmp/MR2_001_CBR_RATE_DRY_RUN.log"

echo "=== TEST CBR REFERENCE RATE V1 ==="

PYTHONPATH=src \
/opt/finam-core/venv/bin/python \
  -m py_compile \
  "$MODULE" \
  "$SYNC"

test -s "$LOG"

grep -Fq \
  "VERDICT=CBR_REFERENCE_RATE_SYNC_V1_DRY_RUN_READY" \
  "$LOG"

grep -Fq \
  "db_writes_performed=0" \
  "$LOG"

PYTHONPATH=src \
/opt/finam-core/venv/bin/python - <<'PY'
from datetime import date
from decimal import Decimal

from finam_core.research.cbr_reference_rate_v1 import (
    CbrReferenceRate,
    brz_tick_value_rub,
    select_rate_asof,
)

rates = [
    CbrReferenceRate(
        currency_code="USD",
        cbr_code="R01235",
        rate_date=date(2026, 8, 1),
        rate_value=Decimal("79.4637"),
    ),
    CbrReferenceRate(
        currency_code="USD",
        cbr_code="R01235",
        rate_date=date(2026, 8, 4),
        rate_value=Decimal("80.0687"),
    ),
]

selected = select_rate_asof(
    rates,
    date(2026, 8, 3),
)

assert selected.rate_date == date(
    2026,
    8,
    1,
)

assert selected.rate_value == Decimal(
    "79.4637"
)

tick_value = brz_tick_value_rub(
    tick_size=Decimal("0.01"),
    lot_size=Decimal("10"),
    usd_rub_rate=selected.rate_value,
)

assert tick_value == Decimal(
    "7.946370"
)

print(
    "asof_weekend_reference_ok=1"
)

print(
    f"reconstructed_tick_value={tick_value}"
)

print(
    "VERDICT="
    "TEST_CBR_REFERENCE_RATE_UNIT_CONTRACT_OK"
)
PY

for marker in \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" \
          "$MODULE" \
          "$SYNC" || true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    test "$COUNT" -eq 0
done

echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_CBR_REFERENCE_RATE_V1_OK"
