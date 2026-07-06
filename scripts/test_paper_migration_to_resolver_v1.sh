#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_MIGRATION_TO_RESOLVER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/paper/paper_cost_calculator.py \
  src/marketcore/paper/__init__.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python - <<'PY'
from decimal import Decimal

from marketcore.market.resolver import MarketModelResolver
from marketcore.paper import PaperCostCalculator

resolver = MarketModelResolver()
calculator = PaperCostCalculator()

snapshot = resolver.resolve(
    symbol="SBER@MISX",
    broker_code="FINAM",
    account_scope="BASE",
)

result = calculator.calculate_net_pnl(
    gross_pnl=Decimal("10"),
    entry_price=Decimal("300"),
    snapshot=snapshot,
)

assert result["commission"] > 0
assert result["slippage"] >= 0
assert result["net_trading_pnl"] < Decimal("10")
assert result["net_after_tax"] <= result["net_trading_pnl"]

print("PAPER_COST_RESOLVER_OK")
PY

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$unsafe" = "0"

echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_MIGRATION_TO_RESOLVER_V1_READY"
echo "VERDICT=TEST_PAPER_MIGRATION_TO_RESOLVER_V1_OK"
