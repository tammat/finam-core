#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_TREND_PULLBACK_EQUITY_COST_FORMULA_V1 ==="

python - <<'PY'
from decimal import Decimal

from scripts.research.build_trend_pullback_canonical_cost_validation_v1 import (
    equity_round_trip_commission,
    equity_round_trip_slippage,
)

commission = equity_round_trip_commission(
    entry_notional=Decimal("100000"),
    exit_notional=Decimal("101000"),
    commission_per_trade=Decimal("0.01"),
    commission_pct=Decimal("0.0005"),
)

expected_commission = (
    Decimal("0.02")
    + Decimal("201000") * Decimal("0.0005")
)

if commission != expected_commission:
    raise SystemExit(
        "ERROR=EQUITY_COMMISSION_FORMULA_MISMATCH "
        f"expected={expected_commission} "
        f"actual={commission}"
    )

slippage = equity_round_trip_slippage(
    slippage_per_trade=Decimal("0.01"),
)

if slippage != Decimal("0.02"):
    raise SystemExit(
        "ERROR=EQUITY_SLIPPAGE_FORMULA_MISMATCH "
        f"actual={slippage}"
    )

print(f"round_trip_commission={commission}")
print(f"round_trip_slippage={slippage}")
print("commission_per_trade_semantics=PER_SIDE")
print("commission_pct_semantics=ENTRY_PLUS_EXIT_TURNOVER")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("economic_edge_claimed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TEST_TREND_PULLBACK_EQUITY_COST_FORMULA_V1_OK"
)
PY
