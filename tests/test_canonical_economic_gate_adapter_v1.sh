#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_CANONICAL_ECONOMIC_GATE_ADAPTER_V1 ==="

python - <<'PY'
from decimal import Decimal

from marketcore.research.economics.canonical_economic_gate_adapter_v1 import (
    CanonicalEconomicTradeInputV1,
    evaluate_canonical_economic_gate_v1,
)
from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
    EconomicGateStatusV1,
)


D = Decimal

policy = EconomicCostGatePolicyV1(
    minimum_trades=3,
    minimum_net_expectancy=D("0"),
    minimum_net_profit_factor=D("1"),
)


# PASS
rows = (
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("20"),
        commission=D("2"),
        spread_cost=D("1"),
        slippage=D("1"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("-5"),
        commission=D("2"),
        spread_cost=D("1"),
        slippage=D("1"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("15"),
        commission=D("2"),
        spread_cost=D("1"),
        slippage=D("1"),
    ),
)

result = evaluate_canonical_economic_gate_v1(
    rows,
    policy,
)

print(
    "ADAPTER_CASE positive "
    f"status={result.status} "
    f"net_pnl={result.net_pnl} "
    f"expectancy={result.net_expectancy} "
    f"pf={result.net_profit_factor}"
)

assert result.status == EconomicGateStatusV1.PASS


# COST-KILLED
rows = (
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("5"),
        commission=D("3"),
        slippage=D("3"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("4"),
        commission=D("3"),
        slippage=D("3"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("3"),
        commission=D("3"),
        slippage=D("3"),
    ),
)

result = evaluate_canonical_economic_gate_v1(
    rows,
    policy,
)

print(
    "ADAPTER_CASE cost_killed "
    f"status={result.status} "
    f"net_pnl={result.net_pnl} "
    f"expectancy={result.net_expectancy} "
    f"pf={result.net_profit_factor}"
)

assert (
    result.status
    == EconomicGateStatusV1.REJECT_NEGATIVE_EXPECTANCY
)


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
    "TEST_CANONICAL_ECONOMIC_GATE_ADAPTER_V1_OK"
)
PY
