#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE WRITER ATTRIBUTION GATE AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_trade_writer_attribution_gate_audit_v1.py \
  src/finam_core/strategy/signal_strategy_attribution_gate_v1.py \
  src/finam_core/strategy/signal_strategy_discovery_repository_v1.py

PYTHONPATH=src python3 src/scripts/research/build_trade_writer_attribution_gate_audit_v1.py \
  | tee /tmp/trade_writer_attribution_gate_audit_v1.log

grep -q "TRADE_WRITER_ATTRIBUTION_GATE_AUDIT_V1_OK" /tmp/trade_writer_attribution_gate_audit_v1.log
grep -q "VERDICT=TRADE_WRITER_ATTRIBUTION_GATE_AUDIT_READY" /tmp/trade_writer_attribution_gate_audit_v1.log
grep -q "TRADE_WRITER_AUDIT_SUMMARY" /tmp/trade_writer_attribution_gate_audit_v1.log
grep -q "TRADE_WRITER_ROW" /tmp/trade_writer_attribution_gate_audit_v1.log

echo
echo "=== PRIMARY / REVIEW CANDIDATES ==="
grep -E "PRIMARY_CANDIDATES=|INSERT_REVIEW=|FILL_LOGGER_CANDIDATES=" \
  /tmp/trade_writer_attribution_gate_audit_v1.log

echo TEST_TRADE_WRITER_ATTRIBUTION_GATE_AUDIT_V1_OK
