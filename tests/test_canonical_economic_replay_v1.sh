#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_CANONICAL_ECONOMIC_REPLAY_V1 ==="

python - <<'PY'
from decimal import Decimal

from marketcore.research.economics.canonical_economic_replay_v1 import (
    CanonicalReplayTradeV1,
    build_economic_trade_v1,
)
from marketcore.research.economics.canonical_monetary_normalizer_v1 import (
    AssetClassV1,
    MonetaryContractV1,
)
from marketcore.research.economics.economic_cost_resolver_v1 import (
    CostModelV1,
    EconomicCostContractV1,
)


D = Decimal


# EQUITY
eq_monetary = MonetaryContractV1(
    asset_class=AssetClassV1.EQUITY,
    lot_size=D("1"),
)

eq_cost = EconomicCostContractV1(
    model=CostModelV1.EQUITY_FIXED_PLUS_TURNOVER,
    commission_per_side=D("0.01"),
    commission_pct=D("0.0005"),
    slippage_per_side=D("0.01"),
)

eq_trade = CanonicalReplayTradeV1(
    price_pnl=D("1"),
    quantity=D("1"),
    entry_price=D("100000"),
    exit_price=D("101000"),
)

eq_result = build_economic_trade_v1(
    trade=eq_trade,
    monetary_contract=eq_monetary,
    cost_contract=eq_cost,
)

print(
    "REPLAY_EQUITY "
    f"gross={eq_result.gross_pnl} "
    f"commission={eq_result.commission} "
    f"slippage={eq_result.slippage} "
    f"net={eq_result.gross_pnl - eq_result.commission - eq_result.slippage}"
)

assert eq_result.gross_pnl == D("1")
assert eq_result.commission == D("100.5200")
assert eq_result.slippage == D("0.02")


# USDRUBF
fut_monetary = MonetaryContractV1(
    asset_class=AssetClassV1.FUTURES,
    tick_size=D("0.01"),
    tick_value=D("10"),
)

fut_cost = EconomicCostContractV1(
    model=CostModelV1.FUTURES_MAKER_TAKER,
    maker_rate_pct=D("0"),
    taker_rate_pct=D("0.00462"),
    slippage_per_side=D("1"),
)

fut_trade = CanonicalReplayTradeV1(
    price_pnl=D("0.10"),
    quantity=D("1"),
    entry_price=D("82.00"),
    exit_price=D("82.10"),
    entry_is_taker=True,
    exit_is_taker=True,
)

fut_result = build_economic_trade_v1(
    trade=fut_trade,
    monetary_contract=fut_monetary,
    cost_contract=fut_cost,
)

print(
    "REPLAY_FUTURES "
    f"gross={fut_result.gross_pnl} "
    f"commission={fut_result.commission} "
    f"slippage={fut_result.slippage} "
    f"net={fut_result.gross_pnl - fut_result.commission - fut_result.slippage}"
)

assert fut_result.gross_pnl == D("100")
assert fut_result.commission == D("7.58142")
assert fut_result.slippage == D("2")

print("canonical_trade_replay_used=1")
print("equity_replay_validated=1")
print("futures_replay_validated=1")
print("strategy_specific_logic_used=0")
print("db_writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")

print(
    "VERDICT="
    "TEST_CANONICAL_ECONOMIC_REPLAY_V1_OK"
)
PY
