#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TODAY PNL UNKNOWN TRADE ATTRIBUTION APPLY V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/apply_today_pnl_unknown_trade_attribution_v1.py

echo
echo "=== DRY RUN ==="
PYTHONPATH=src python3 src/scripts/runtime/apply_today_pnl_unknown_trade_attribution_v1.py \
  | tee /tmp/today_pnl_unknown_trade_attribution_apply_v1_dry.log

grep -q "TODAY_PNL_UNKNOWN_TRADE_ATTRIBUTION_APPLY_V1_OK" /tmp/today_pnl_unknown_trade_attribution_apply_v1_dry.log
grep -q "VERDICT=TODAY_PNL_UNKNOWN_ATTRIBUTION_APPLY_DRY_RUN_READY" /tmp/today_pnl_unknown_trade_attribution_apply_v1_dry.log
grep -q "db_update=0" /tmp/today_pnl_unknown_trade_attribution_apply_v1_dry.log
grep -q "safe_apply_candidates=1" /tmp/today_pnl_unknown_trade_attribution_apply_v1_dry.log

echo
echo "=== APPLY ==="
APPLY=1 PYTHONPATH=src python3 src/scripts/runtime/apply_today_pnl_unknown_trade_attribution_v1.py \
  | tee /tmp/today_pnl_unknown_trade_attribution_apply_v1_apply.log

grep -q "TODAY_PNL_UNKNOWN_TRADE_ATTRIBUTION_APPLY_V1_OK" /tmp/today_pnl_unknown_trade_attribution_apply_v1_apply.log
grep -q "VERDICT=TODAY_PNL_UNKNOWN_ATTRIBUTION_APPLY_OK" /tmp/today_pnl_unknown_trade_attribution_apply_v1_apply.log
grep -q "db_update=1" /tmp/today_pnl_unknown_trade_attribution_apply_v1_apply.log
grep -q "unknown_rows_after=0" /tmp/today_pnl_unknown_trade_attribution_apply_v1_apply.log

echo
echo "=== VERIFY TODAY PNL JSON ==="
curl -fsS http://127.0.0.1:8088/today-pnl/json \
  | tee /tmp/today_pnl_after_unknown_attribution_fix_v1.json \
  | grep -E '"trades_today"|"closed_cycles"|"net_pnl"|"context_clean"|"verdict"'

grep -q '"context_clean":1' /tmp/today_pnl_after_unknown_attribution_fix_v1.json || \
grep -q '"context_clean": 1' /tmp/today_pnl_after_unknown_attribution_fix_v1.json

grep -q '"verdict":"TODAY_CLOSED_PNL_STATUS_OK"' /tmp/today_pnl_after_unknown_attribution_fix_v1.json || \
grep -q '"verdict": "TODAY_CLOSED_PNL_STATUS_OK"' /tmp/today_pnl_after_unknown_attribution_fix_v1.json

echo TEST_TODAY_PNL_UNKNOWN_TRADE_ATTRIBUTION_APPLY_V1_OK
