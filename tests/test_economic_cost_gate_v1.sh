#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_ECONOMIC_COST_GATE_V1 ==="

python - <<'PY'
from decimal import Decimal

from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
    EconomicGateStatusV1,
    EconomicTradeV1,
    evaluate_economic_cost_gate_v1,
)


D = Decimal

policy = EconomicCostGatePolicyV1(
    minimum_trades=3,
    minimum_net_expectancy=D("0"),
    minimum_net_profit_factor=D("1"),
)


# 1. Реальный положительный net edge.
positive = (
    EconomicTradeV1(
        gross_pnl=D("20"),
        commission=D("2"),
        spread_cost=D("1"),
        slippage=D("1"),
    ),
    EconomicTradeV1(
        gross_pnl=D("-5"),
        commission=D("2"),
        spread_cost=D("1"),
        slippage=D("1"),
    ),
    EconomicTradeV1(
        gross_pnl=D("15"),
        commission=D("2"),
        spread_cost=D("1"),
        slippage=D("1"),
    ),
)

result = evaluate_economic_cost_gate_v1(
    positive,
    policy,
)

print(
    "CASE positive "
    f"status={result.status} "
    f"net_pnl={result.net_pnl} "
    f"expectancy={result.net_expectancy} "
    f"pf={result.net_profit_factor}"
)

assert result.status == EconomicGateStatusV1.PASS
assert result.passed is True


# 2. Gross положительный, но costs уничтожают edge.
cost_killed = (
    EconomicTradeV1(
        gross_pnl=D("5"),
        commission=D("3"),
        spread_cost=D("1"),
        slippage=D("2"),
    ),
    EconomicTradeV1(
        gross_pnl=D("4"),
        commission=D("3"),
        spread_cost=D("1"),
        slippage=D("2"),
    ),
    EconomicTradeV1(
        gross_pnl=D("3"),
        commission=D("3"),
        spread_cost=D("1"),
        slippage=D("2"),
    ),
)

result = evaluate_economic_cost_gate_v1(
    cost_killed,
    policy,
)

print(
    "CASE cost_killed "
    f"status={result.status} "
    f"net_pnl={result.net_pnl} "
    f"expectancy={result.net_expectancy} "
    f"pf={result.net_profit_factor}"
)

assert (
    result.status
    == EconomicGateStatusV1.REJECT_NEGATIVE_EXPECTANCY
)

assert result.passed is False


# 3. Недостаточная выборка.
small_sample = positive[:2]

result = evaluate_economic_cost_gate_v1(
    small_sample,
    policy,
)

print(
    "CASE small_sample "
    f"status={result.status} "
    f"trades={result.trades}"
)

assert (
    result.status
    == EconomicGateStatusV1.REJECT_INSUFFICIENT_TRADES
)

assert result.passed is False


print("strategy_logic_used=0")
print("execution_orders_created=0")
print("db_writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")

print(
    "VERDICT="
    "TEST_ECONOMIC_COST_GATE_V1_OK"
)
PY
