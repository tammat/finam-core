#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT GUARD POSTGRES LOGGER ENFORCEMENT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/storage/postgres_logger.py
python3 -m py_compile src/finam_core/storage/trade_context_guard_v1.py

grep -q "TRADE_CONTEXT_GUARD_POSTGRES_LOGGER_ENFORCEMENT_V1" src/finam_core/storage/postgres_logger.py
grep -q "_normalize_trade_context_before_insert_v1" src/finam_core/storage/postgres_logger.py
grep -q "TRADE_CONTEXT_GUARD_POSTGRES_LOGGER_NORMALIZED" src/finam_core/storage/postgres_logger.py
grep -q "TradeContextGuardV1" src/finam_core/storage/postgres_logger.py

# The storage guard must receive resolved attribution values. Referencing local
# names before assignment silently rolls back both canonical fills and trades.
grep -q "strategy=attribution_decision.strategy" src/finam_core/storage/postgres_logger.py
grep -q "timeframe=attribution_decision.timeframe" src/finam_core/storage/postgres_logger.py
grep -q "continuous_symbol=attribution_decision.continuous_symbol" src/finam_core/storage/postgres_logger.py

# Python source must never be embedded in the SQL statement passed to psycopg.
if sed -n '/cur.execute(/,/INSERT INTO trades/p' src/finam_core/storage/postgres_logger.py \
    | grep -q 'strategy, timeframe, continuous_symbol, payload ='; then
    echo "FAIL: Python normalization code is embedded in INSERT INTO trades SQL" >&2
    exit 1
fi

PYTHONPATH=src python3 - <<'PY'
from finam_core.storage.trade_context_guard_v1 import TradeContextGuardV1

guard = TradeContextGuardV1()

decision = guard.normalize(
    symbol="USDRUBF@RTSX",
    strategy="",
    timeframe="",
    continuous_symbol="",
    payload={
        "strategy": "USDRUB_REGIME",
        "timeframe": "LIVE",
        "continuous_symbol": "USDRUB_CONT",
        "trade_context_snapshot": {
            "strategy": "USDRUB_REGIME",
            "timeframe": "LIVE",
            "continuous_symbol": "USDRUB_CONT",
        },
    },
)
assert decision.allowed
assert decision.strategy == "USDRUB_REGIME"
assert decision.timeframe == "LIVE"
assert decision.continuous_symbol == "USDRUB_CONT"

print("TRADE_CONTEXT_GUARD_POSTGRES_LOGGER_ENFORCEMENT_SMOKE_OK")
PY

echo TEST_TRADE_CONTEXT_GUARD_POSTGRES_LOGGER_ENFORCEMENT_V1_OK
