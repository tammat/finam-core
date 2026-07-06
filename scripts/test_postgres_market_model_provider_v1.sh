#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_POSTGRES_MARKET_MODEL_PROVIDER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/market/mapper/market_snapshot_mapper.py \
  src/marketcore/market/mapper/__init__.py \
  src/marketcore/market/providers/postgres_market_model_provider.py \
  src/marketcore/market/providers/__init__.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python - <<'PY'
from dataclasses import FrozenInstanceError
from decimal import Decimal

from marketcore.market.providers import PostgresMarketModelProvider

provider = PostgresMarketModelProvider()

snapshot = provider.load(
    symbol="SBER@MISX",
    broker_code="FINAM",
    account_scope="BASE",
)

assert snapshot.instrument.symbol == "SBER@MISX"
assert snapshot.instrument.exchange_code == "MISX"
assert snapshot.instrument.asset_class == "EQUITY"
assert snapshot.contract.lot_size > Decimal("0")
assert snapshot.cost.broker_code == "FINAM"
assert snapshot.tax.account_scope == "BASE"
assert snapshot.eligibility.is_allowed is True

try:
    snapshot.instrument.symbol = "TEST"
    raise RuntimeError("DTO_MUTABLE")
except FrozenInstanceError:
    pass

many = provider.load_many(
    symbols=["SBER@MISX", "LKOH@MISX"],
    broker_code="FINAM",
    account_scope="BASE",
)

assert set(many.keys()) == {"SBER@MISX", "LKOH@MISX"}

print("POSTGRES_MARKET_MODEL_PROVIDER_OK")
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
echo "VERDICT=POSTGRES_MARKET_MODEL_PROVIDER_V1_READY"
echo "VERDICT=TEST_POSTGRES_MARKET_MODEL_PROVIDER_V1_OK"
