#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY SHADOW EDGE SCORECARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_shadow_edge_scorecard_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_shadow_edge_scorecard_v1.py \
  | tee /tmp/equity_shadow_edge_scorecard_v1.log

grep -q "EQUITY_SHADOW_EDGE_SCORECARD_V1_OK" /tmp/equity_shadow_edge_scorecard_v1.log
grep -q "EQUITY_SHADOW_EDGE_SCORECARD_SUMMARY" /tmp/equity_shadow_edge_scorecard_v1.log
grep -q "runtime_equity_rows=" /tmp/equity_shadow_edge_scorecard_v1.log
grep -q "enabled_equities=" /tmp/equity_shadow_edge_scorecard_v1.log
grep -q "equities_with_bars=" /tmp/equity_shadow_edge_scorecard_v1.log
grep -q "signals_total=" /tmp/equity_shadow_edge_scorecard_v1.log
grep -q "equity_clean_runtime_trades=" /tmp/equity_shadow_edge_scorecard_v1.log
grep -q "VERDICT=" /tmp/equity_shadow_edge_scorecard_v1.log
grep -q "db_update=0" /tmp/equity_shadow_edge_scorecard_v1.log

echo
echo "=== EQUITY SHADOW EDGE SUMMARY ==="
grep -E "EQUITY_RUNTIME_ROW|EQUITY_BAR_ROW|EQUITY_SIGNAL_ROW|EQUITY_INTENT_ROW|EQUITY_TRADE_ROW|runtime_equity_rows=|enabled_equities=|equities_with_bars=|equities_enabled_with_bars=|signals_total=|execution_intents_total=|equity_trades_total=|equity_clean_runtime_trades=|VERDICT=" \
  /tmp/equity_shadow_edge_scorecard_v1.log | head -160

echo TEST_EQUITY_SHADOW_EDGE_SCORECARD_V1_OK
