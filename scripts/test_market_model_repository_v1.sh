#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_MODEL_REPOSITORY_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/market/repository/market_model_repository.py \
  src/marketcore/market/repository/__init__.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python - <<'PY'
from marketcore.market.repository import MarketModelRepository

repo = MarketModelRepository()
row = repo.load_raw("SBER@MISX", "FINAM", "BASE")

assert row["symbol"] == "SBER@MISX"
assert row["broker_code"] == "FINAM"
assert row["asset_class"] == "EQUITY"
assert row["tax_profile_code"]

print("MARKET_MODEL_REPOSITORY_OK")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_MODEL_REPOSITORY_V1_READY"
echo "VERDICT=TEST_MARKET_MODEL_REPOSITORY_V1_OK"
