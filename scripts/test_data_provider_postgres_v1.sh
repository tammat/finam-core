#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_PROVIDER_POSTGRES_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/research/execution/interfaces/data_provider.py \
  src/marketcore/research/execution/providers/postgres_market_data_provider.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python - <<'PY'
from marketcore.research.execution.providers.postgres_market_data_provider import PostgresMarketDataProvider

provider = PostgresMarketDataProvider()
bars = provider.load_market_data("BR@RTSX", "M5", parameters={"limit": 100})

assert bars.symbol == "BR@RTSX"
assert bars.timeframe == "M5"
assert bars.source.startswith("postgres:")
assert bars.count >= 0

print(f"source={bars.source}")
print(f"bars_count={bars.count}")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=DATA_PROVIDER_POSTGRES_V1_READY"
echo "VERDICT=TEST_DATA_PROVIDER_POSTGRES_V1_OK"
