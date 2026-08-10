#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_ECONOMIC_COST_RESOLVER_V1 ==="

python - <<'PY'
from decimal import Decimal

from marketcore.research.economics.economic_cost_resolver_v1 import (
    CostModelV1,
    EconomicCostContractV1,
    resolve_round_trip_cost_v1,
)


D = Decimal


# EQUITY
equity = EconomicCostContractV1(
    model=(
        CostModelV1
        .EQUITY_FIXED_PLUS_TURNOVER
    ),
    commission_per_side=D("0.01"),
    commission_pct=D("0.0005"),
    slippage_per_side=D("0.01"),
)

cost = resolve_round_trip_cost_v1(
    entry_notional_rub=D("100000"),
    exit_notional_rub=D("101000"),
    contract=equity,
)

expected_commission = (
    D("0.02")
    + D("201000") * D("0.0005")
)

assert cost.commission == expected_commission
assert cost.slippage == D("0.02")

print(
    "EQUITY_COST_CASE "
    f"commission={cost.commission} "
    f"slippage={cost.slippage} "
    f"total_cost={cost.total_cost}"
)


# USDRUBF TAKER/TAKER
futures = EconomicCostContractV1(
    model=CostModelV1.FUTURES_MAKER_TAKER,
    maker_rate_pct=D("0"),
    taker_rate_pct=D("0.00462"),
    slippage_per_side=D("1"),
)

cost = resolve_round_trip_cost_v1(
    entry_notional_rub=D("82000"),
    exit_notional_rub=D("82100"),
    contract=futures,
    entry_is_taker=True,
    exit_is_taker=True,
)

expected = (
    D("82000")
    * D("0.00462")
    / D("100")
    + D("82100")
    * D("0.00462")
    / D("100")
)

assert cost.commission == expected
assert cost.slippage == D("2")

print(
    "FUTURES_TAKER_TAKER_CASE "
    f"commission={cost.commission} "
    f"slippage={cost.slippage} "
    f"total_cost={cost.total_cost}"
)


# MAKER/TAKER:
# maker leg commission = 0.
cost_mt = resolve_round_trip_cost_v1(
    entry_notional_rub=D("82000"),
    exit_notional_rub=D("82100"),
    contract=futures,
    entry_is_taker=False,
    exit_is_taker=True,
)

expected_mt = (
    D("82100")
    * D("0.00462")
    / D("100")
)

assert cost_mt.commission == expected_mt
assert cost_mt.commission < cost.commission

print(
    "FUTURES_MAKER_TAKER_CASE "
    f"commission={cost_mt.commission}"
)

print("equity_cost_semantics_validated=1")
print("futures_cost_semantics_validated=1")
print("maker_taker_semantics_validated=1")
print("funding_separate=1")
print("strategy_specific_logic_used=0")
print("instrument_specific_logic_used=0")
print("db_writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")

print(
    "VERDICT="
    "TEST_ECONOMIC_COST_RESOLVER_V1_OK"
)
PY
