#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT GUARD ALT WRITER PATCH V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py
python3 -m py_compile src/finam_core/storage/trade_context_guard_v1.py

grep -q "TRADE_CONTEXT_GUARD_ALT_WRITER_PATCH_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "_ensure_trade_context_before_log_trade_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "TradeContextGuardV1" src/finam_core/pipelines/paper_pipeline.py
grep -q "trade = self._ensure_trade_context_before_log_trade_v1(trade)" src/finam_core/pipelines/paper_pipeline.py
grep -q "TRADE_CONTEXT_GUARD_ALT_WRITER_NORMALIZED" src/finam_core/pipelines/paper_pipeline.py

PYTHONPATH=src python3 - <<'PY'
from finam_core.storage.trade_context_guard_v1 import TradeContextGuardV1

guard = TradeContextGuardV1()

decision = guard.normalize(
    symbol="USDRUBF@RTSX",
    strategy=None,
    timeframe=None,
    continuous_symbol=None,
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

print("TRADE_CONTEXT_GUARD_ALT_WRITER_PATCH_SMOKE_OK")
PY

echo TEST_TRADE_CONTEXT_GUARD_ALT_WRITER_PATCH_V1_OK
