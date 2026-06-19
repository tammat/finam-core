#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY MTF CALLBACK REACHABILITY AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_mtf_callback_reachability_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_mtf_callback_reachability_audit_v1.py \
  | tee /tmp/equity_mtf_callback_reachability_audit_v1.log

grep -q "EQUITY_MTF_CALLBACK_REACHABILITY_AUDIT_V1_OK" /tmp/equity_mtf_callback_reachability_audit_v1.log
grep -q "EQUITY_MTF_CALLBACK_REACHABILITY_AUDIT_SUMMARY" /tmp/equity_mtf_callback_reachability_audit_v1.log
grep -q "callback_hits=" /tmp/equity_mtf_callback_reachability_audit_v1.log
grep -q "equity_handler_hits=" /tmp/equity_mtf_callback_reachability_audit_v1.log
grep -q "VERDICT=" /tmp/equity_mtf_callback_reachability_audit_v1.log
grep -q "db_update=0" /tmp/equity_mtf_callback_reachability_audit_v1.log

echo
echo "=== EQUITY MTF CALLBACK REACHABILITY SUMMARY ==="
grep -E "EQUITY_MTF_CALLBACK_CODE_HIT|files_with_hits=|callback_hits=|equity_handler_hits=|br_ng_handler_hits=|market_bar_writer_hits=|VERDICT=" \
  /tmp/equity_mtf_callback_reachability_audit_v1.log | head -240

echo TEST_EQUITY_MTF_CALLBACK_REACHABILITY_AUDIT_V1_OK
