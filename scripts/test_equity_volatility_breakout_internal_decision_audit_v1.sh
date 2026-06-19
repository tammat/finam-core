#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY VOLATILITY BREAKOUT INTERNAL DECISION AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_volatility_breakout_internal_decision_audit_v1.py

PYTHONPATH=src \
ACTIVE_SINCE_UTC="${ACTIVE_SINCE_UTC:-2026-06-19 07:24:35+00}" \
python3 src/scripts/research/build_equity_volatility_breakout_internal_decision_audit_v1.py \
  | tee /tmp/equity_volatility_breakout_internal_decision_audit_v1.log

grep -q "EQUITY_VOLATILITY_BREAKOUT_INTERNAL_DECISION_AUDIT_V1_OK" /tmp/equity_volatility_breakout_internal_decision_audit_v1.log
grep -q "EQUITY_VOL_BREAKOUT_INTERNAL_DECISION_AUDIT_SUMMARY" /tmp/equity_volatility_breakout_internal_decision_audit_v1.log
grep -q "default_min_atr_pct=" /tmp/equity_volatility_breakout_internal_decision_audit_v1.log
grep -q "default_volume_mult=" /tmp/equity_volatility_breakout_internal_decision_audit_v1.log
grep -q "blocked_by_atr=" /tmp/equity_volatility_breakout_internal_decision_audit_v1.log
grep -q "blocked_by_volume=" /tmp/equity_volatility_breakout_internal_decision_audit_v1.log
grep -q "blocked_by_breakout=" /tmp/equity_volatility_breakout_internal_decision_audit_v1.log
grep -q "VERDICT=" /tmp/equity_volatility_breakout_internal_decision_audit_v1.log
grep -q "db_update=0" /tmp/equity_volatility_breakout_internal_decision_audit_v1.log

echo
echo "=== EQUITY VOLATILITY BREAKOUT INTERNAL DECISION SUMMARY ==="
grep -E "EQUITY_VOL_BREAKOUT_SOURCE_PARAMS|default_|EQUITY_VOL_BREAKOUT_RUNTIME_ROW|EQUITY_VOL_BREAKOUT_BAR_DECISION_ROW|rows_total=|blocked_by_|proxy_ready_rows=|VERDICT=" \
  /tmp/equity_volatility_breakout_internal_decision_audit_v1.log | head -260

echo TEST_EQUITY_VOLATILITY_BREAKOUT_INTERNAL_DECISION_AUDIT_V1_OK
