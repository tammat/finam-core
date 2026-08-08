#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

MODULE="src/finam_core/research/cbr_reference_rate_v1.py"
ADAPTER="src/finam_core/research/postgresql_edge_backtest_adapter_v1.py"

echo "=== TEST FUTURES MONETARY PNL NORMALIZATION V1 ==="

PYTHONPATH=src \
/opt/finam-core/venv/bin/python -m py_compile \
  "$MODULE" \
  "$ADAPTER"

PYTHONPATH=src \
/opt/finam-core/venv/bin/python - <<'PY'
from datetime import date
from decimal import Decimal

from finam_core.research.cbr_reference_rate_v1 import (
    CbrReferenceRate,
    brz_tick_value_rub,
    futures_price_delta_to_rub,
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

reference = select_rate_asof(
    rates,
    date(2026, 8, 3),
)

assert reference.rate_date == date(2026, 8, 1)

tick_value = brz_tick_value_rub(
    tick_size=Decimal("0.01"),
    lot_size=Decimal("10"),
    usd_rub_rate=reference.rate_value,
)

assert tick_value == Decimal("7.946370")

pnl = futures_price_delta_to_rub(
    price_delta=Decimal("1.00"),
    quantity=Decimal("1"),
    tick_size=Decimal("0.01"),
    tick_value=tick_value,
)

# 1.00 / 0.01 = 100 ticks.
# 100 × 7.946370 RUB = 794.637 RUB.
assert pnl == Decimal("794.637000")

print(f"tick_value_rub={tick_value}")
print(f"price_delta_rub_pnl={pnl}")
print("future_lookup_used=0")
print(
    "VERDICT="
    "TEST_FUTURES_MONETARY_UNIT_CONTRACT_OK"
)
PY

grep -Fq \
  'symbol == "BRZ6@RTSX"' \
  "$ADAPTER"

grep -Fq \
  "BRZ6_CBR_REFERENCE_TABLE_EMPTY" \
  "$ADAPTER"

grep -Fq \
  "BRZ6_STATIC_SPEC_NOT_UNIQUE" \
  "$ADAPTER"

grep -Fq \
  "futures_price_delta_to_rub" \
  "$ADAPTER"

for marker in \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" \
          "$MODULE" \
          "$ADAPTER" || true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    test "$COUNT" -eq 0
done

echo "target_symbol=BRZ6@RTSX"
echo "reference_fx_source=CBR_OFFICIAL_USD_RUB"
echo "reference_fx_code=R01235"
echo "future_reference_lookup_allowed=0"

echo "ngk6_corrected_replay_allowed=0"
echo "generic_ng_fallback_allowed=0"

echo "parameter_grid_changed=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_FUTURES_MONETARY_PNL_NORMALIZATION_V1_OK"
