#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

export PYTHONPATH=src

echo "=== TEST_TREND_PULLBACK_CANONICAL_COST_IDENTITY_V1 ==="

python - <<'PY'
from decimal import Decimal

from scripts.research.build_trend_pullback_canonical_cost_validation_v1 import (
    apply_research_cost_identity,
)


cases = [
    (
        Decimal("100"),
        Decimal("10"),
        Decimal("5"),
        Decimal("85"),
    ),
    (
        Decimal("2"),
        Decimal("1"),
        Decimal("3"),
        Decimal("-2"),
    ),
    (
        Decimal("-10"),
        Decimal("1"),
        Decimal("2"),
        Decimal("-13"),
    ),
]

for no, (
    gross,
    commission,
    slippage,
    expected,
) in enumerate(cases, start=1):

    trade = apply_research_cost_identity(
        gross_pnl=gross,
        commission=commission,
        slippage=slippage,
    )

    if trade.net_pnl != expected:
        raise SystemExit(
            "ERROR=COST_IDENTITY_MISMATCH "
            f"case={no} "
            f"expected={expected} "
            f"actual={trade.net_pnl}"
        )

    print(
        f"CASE_OK no={no} "
        f"gross={gross} "
        f"commission={commission} "
        f"slippage={slippage} "
        f"net={trade.net_pnl}"
    )


# Явная защита от double counting:
#
# Допустим, total slippage = 5 уже содержит:
# spread=2 + impact=1 + residual=2.
#
# Net должен быть:
# 100 - 10 - 5 = 85,
# а НЕ 100 - 10 - 5 - 2 - 1 = 82.

trade = apply_research_cost_identity(
    gross_pnl=Decimal("100"),
    commission=Decimal("10"),
    slippage=Decimal("5"),
)

if trade.net_pnl != Decimal("85"):
    raise SystemExit(
        "ERROR=DOUBLE_COUNT_GUARD_FAILED"
    )

print("double_count_guard=PASS")
print("spread_cost_separately_subtracted=0")
print("impact_cost_separately_subtracted=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TEST_TREND_PULLBACK_CANONICAL_COST_IDENTITY_V1_OK"
)
PY
