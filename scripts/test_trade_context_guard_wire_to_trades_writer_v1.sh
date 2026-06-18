#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT GUARD WIRE TO TRADES WRITER V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/storage/trade_context_guard_v1.py
python3 -m py_compile src/finam_core/storage/postgres_logger.py
python3 -m py_compile src/finam_core/storage/postgres.py

grep -q "TradeContextGuardV1" src/finam_core/storage/postgres_logger.py
grep -q "TradeContextGuardV1" src/finam_core/storage/postgres.py
grep -q "TRADE_CONTEXT_GUARD_WIRE_TO_TRADES_WRITER_V1" src/finam_core/storage/postgres_logger.py
grep -q "TRADE_CONTEXT_GUARD_WIRE_TO_TRADES_WRITER_V1" src/finam_core/storage/postgres.py
grep -q "trade_context_decision.strategy" src/finam_core/storage/postgres_logger.py
grep -q "trade_context_decision.timeframe" src/finam_core/storage/postgres_logger.py
grep -q "trade_context_decision.continuous_symbol" src/finam_core/storage/postgres_logger.py
grep -q "payload\\[\"strategy\"\\] = strategy" src/finam_core/storage/postgres.py
grep -q "payload\\[\"timeframe\"\\] = timeframe" src/finam_core/storage/postgres.py
grep -q "payload\\[\"continuous_symbol\"\\] = continuous_symbol" src/finam_core/storage/postgres.py

bash scripts/test_today_pnl_attribution_guard_v1.sh

PYTHONPATH=src python3 - <<'PY'
from finam_core.storage.trade_context_guard_v1 import TradeContextGuardV1

guard = TradeContextGuardV1()

decision = guard.normalize(
    symbol="USDRUBF@RTSX",
    strategy=None,
    timeframe=None,
    continuous_symbol=None,
    payload={
        "trade_context_snapshot": {
            "strategy": "USDRUB_REGIME",
            "timeframe": "LIVE",
            "continuous_symbol": "USDRUB_CONT",
        }
    },
)
assert decision.allowed
assert decision.strategy == "USDRUB_REGIME"
assert decision.timeframe == "LIVE"
assert decision.continuous_symbol == "USDRUB_CONT"

decision = guard.normalize(
    symbol="UNKNOWN@RTSX",
    strategy=None,
    timeframe=None,
    continuous_symbol=None,
    payload={},
)
assert not decision.allowed

print("TRADE_CONTEXT_GUARD_WRITER_WIRE_SMOKE_OK")
PY

echo TEST_TRADE_CONTEXT_GUARD_WIRE_TO_TRADES_WRITER_V1_OK
