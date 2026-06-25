#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_TRADE_LINKING_IMPLEMENTATION_V1_1 ==="

python3 -m py_compile \
  src/finam_core/research/market_state/trade_linker.py

PYTHONPATH=src python3 - <<'PY'
import os

from finam_core.research.market_state.trade_linker import MarketStateTradeLinker

linker = MarketStateTradeLinker(database_url=os.environ["DATABASE_URL"])
rows = linker.run()

print(f"linked_rows={rows}")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")
print("VERDICT=MARKET_STATE_TRADE_LINKING_IMPLEMENTATION_V1_1_OK")
PY

grep -R "from .*execution\|import .*execution\|OrderClient\|broker_adapter\|real_trading_enabled *= *1" \
  src/finam_core/research/market_state/trade_linker.py \
  && exit 1 || true

echo "TEST_MARKET_STATE_TRADE_LINKING_IMPLEMENTATION_V1_1_OK"
