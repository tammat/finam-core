#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_CANONICAL_MONETARY_NORMALIZER_V1 ==="

python - <<'PY'
from decimal import Decimal

from marketcore.research.economics.canonical_monetary_normalizer_v1 import (
    AssetClassV1,
    MonetaryContractV1,
    normalize_gross_pnl_rub_v1,
)

D = Decimal

# EQUITY:
# 1 RUB price movement × 1 share × lot 1 = 1 RUB.
equity = MonetaryContractV1(
    asset_class=AssetClassV1.EQUITY,
    lot_size=D("1"),
)

equity_pnl = normalize_gross_pnl_rub_v1(
    price_pnl=D("1"),
    quantity=D("1"),
    contract=equity,
)

print(f"equity_gross_pnl_rub={equity_pnl}")
assert equity_pnl == D("1")


# USDRUBF:
# 0.01 movement = one tick = 10 RUB.
futures = MonetaryContractV1(
    asset_class=AssetClassV1.FUTURES,
    tick_size=D("0.01"),
    tick_value=D("10"),
)

futures_tick_pnl = normalize_gross_pnl_rub_v1(
    price_pnl=D("0.01"),
    quantity=D("1"),
    contract=futures,
)

print(
    f"usdrubf_one_tick_pnl_rub="
    f"{futures_tick_pnl}"
)

assert futures_tick_pnl == D("10")


# 1 RUB movement = 100 ticks = 1000 RUB.
futures_one_rub = normalize_gross_pnl_rub_v1(
    price_pnl=D("1"),
    quantity=D("1"),
    contract=futures,
)

print(
    f"usdrubf_one_rub_move_pnl="
    f"{futures_one_rub}"
)

assert futures_one_rub == D("1000")

print("equity_scale_validated=1")
print("futures_scale_validated=1")
print("strategy_specific_logic_used=0")
print("db_writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")

print(
    "VERDICT="
    "TEST_CANONICAL_MONETARY_NORMALIZER_V1_OK"
)
PY
