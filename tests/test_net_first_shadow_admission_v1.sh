#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_NET_FIRST_SHADOW_ADMISSION_V1 ==="

python - <<'PY'
from decimal import Decimal

from marketcore.research.net_first_shadow_admission_v1 import (
    ShadowAdmissionDecisionV1,
    evaluate_shadow_admission_v1,
)
from marketcore.research.economics.canonical_economic_gate_adapter_v1 import (
    CanonicalEconomicTradeInputV1,
)
from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
)


D = Decimal

policy = EconomicCostGatePolicyV1(
    minimum_trades=3,
    minimum_net_expectancy=D("0"),
    minimum_net_profit_factor=D("1"),
)


rejected = (
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("5"),
        commission=D("4"),
        slippage=D("2"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("4"),
        commission=D("4"),
        slippage=D("2"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("3"),
        commission=D("4"),
        slippage=D("2"),
    ),
)

r = evaluate_shadow_admission_v1(
    economic_trades=rejected,
    policy=policy,
)

print(
    "SHADOW_CASE rejected "
    f"decision={r.decision} "
    f"economic_status={r.economic_result.status} "
    f"production_blocked={int(r.production_blocked)}"
)

assert (
    r.decision
    == ShadowAdmissionDecisionV1.WOULD_REJECT
)
assert r.production_blocked is False


passed = (
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("20"),
        commission=D("2"),
        slippage=D("1"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("-5"),
        commission=D("2"),
        slippage=D("1"),
    ),
    CanonicalEconomicTradeInputV1(
        gross_pnl=D("15"),
        commission=D("2"),
        slippage=D("1"),
    ),
)

r = evaluate_shadow_admission_v1(
    economic_trades=passed,
    policy=policy,
)

print(
    "SHADOW_CASE passed "
    f"decision={r.decision} "
    f"economic_status={r.economic_result.status} "
    f"production_blocked={int(r.production_blocked)}"
)

assert (
    r.decision
    == ShadowAdmissionDecisionV1.WOULD_ADMIT
)
assert r.production_blocked is False

print("shadow_admission_enabled=1")
print("enforced_admission_enabled=0")
print("production_pipeline_changed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")

print(
    "VERDICT="
    "TEST_NET_FIRST_SHADOW_ADMISSION_V1_OK"
)
PY
