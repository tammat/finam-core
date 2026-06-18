#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT NO MISSING GUARD VALIDATION V2 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_trade_context_no_missing_guard_validation_v1.py \
  src/finam_core/storage/postgres_logger.py \
  src/finam_core/strategy/signal_strategy_attribution_gate_v1.py \
  src/finam_core/strategy/signal_strategy_discovery_repository_v1.py

PYTHONPATH=src python3 src/scripts/research/build_trade_context_no_missing_guard_validation_v1.py \
  | tee /tmp/trade_context_no_missing_guard_validation_v2.log

grep -q "TRADE_CONTEXT_NO_MISSING_GUARD_VALIDATION_V1_OK" /tmp/trade_context_no_missing_guard_validation_v2.log
grep -q "VERDICT=TRADE_CONTEXT_NO_MISSING_GUARD_VALIDATION_OK" /tmp/trade_context_no_missing_guard_validation_v2.log
grep -q "FAILURES=none" /tmp/trade_context_no_missing_guard_validation_v2.log
grep -q "strategy_missing_today=0" /tmp/trade_context_no_missing_guard_validation_v2.log
grep -q "timeframe_missing_today=0" /tmp/trade_context_no_missing_guard_validation_v2.log
grep -q "continuous_symbol_missing_today=0" /tmp/trade_context_no_missing_guard_validation_v2.log

echo TEST_TRADE_CONTEXT_NO_MISSING_GUARD_VALIDATION_V2_OK
