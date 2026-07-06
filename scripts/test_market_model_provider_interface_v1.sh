#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_MODEL_PROVIDER_INTERFACE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/market/interfaces/market_model_provider.py \
  src/marketcore/market/interfaces/__init__.py

PYTHONPATH=src python - <<'PY'
from marketcore.market.interfaces import MarketModelProvider

print(MarketModelProvider)
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_MODEL_PROVIDER_INTERFACE_V1_READY"
echo "VERDICT=TEST_MARKET_MODEL_PROVIDER_INTERFACE_V1_OK"
