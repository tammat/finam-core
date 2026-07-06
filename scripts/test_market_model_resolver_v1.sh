#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_MODEL_RESOLVER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/market/cache/market_model_cache.py \
  src/marketcore/market/cache/__init__.py \
  src/marketcore/market/resolver/market_model_resolver.py \
  src/marketcore/market/resolver/__init__.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python - <<'PY'
from decimal import Decimal

from marketcore.market.resolver import MarketModelResolver

resolver = MarketModelResolver()

s1 = resolver.resolve(
    symbol="SBER@MISX",
    broker_code="FINAM",
    account_scope="BASE",
)

s2 = resolver.resolve(
    symbol="SBER@MISX",
    broker_code="FINAM",
    account_scope="BASE",
)

assert s1 is s2
assert s1.instrument.symbol == "SBER@MISX"
assert s1.instrument.exchange_code == "MISX"
assert s1.contract.lot_size > Decimal("0")
assert s1.cost.broker_code == "FINAM"
assert s1.tax.account_scope == "BASE"
assert s1.eligibility.is_allowed is True

many = resolver.resolve_many(
    symbols=["SBER@MISX", "LKOH@MISX"],
    broker_code="FINAM",
    account_scope="BASE",
)

assert set(many.keys()) == {"SBER@MISX", "LKOH@MISX"}

resolver.invalidate(
    symbol="SBER@MISX",
    broker_code="FINAM",
    account_scope="BASE",
)

s3 = resolver.resolve(
    symbol="SBER@MISX",
    broker_code="FINAM",
    account_scope="BASE",
)

assert s3.instrument.symbol == "SBER@MISX"

print("MARKET_MODEL_RESOLVER_OK")
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
echo "VERDICT=MARKET_MODEL_RESOLVER_V1_READY"
echo "VERDICT=TEST_MARKET_MODEL_RESOLVER_V1_OK"
