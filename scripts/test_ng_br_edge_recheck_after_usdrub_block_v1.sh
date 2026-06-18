#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST NG BR EDGE RECHECK AFTER USDRUB BLOCK V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_ng_br_edge_recheck_after_usdrub_block_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_ng_br_edge_recheck_after_usdrub_block_v1.py \
  | tee /tmp/ng_br_edge_recheck_after_usdrub_block_v1.log

grep -q "NG_BR_EDGE_RECHECK_AFTER_USDRUB_BLOCK_V1_OK" /tmp/ng_br_edge_recheck_after_usdrub_block_v1.log
grep -q "NG_BR_EDGE_RECHECK_SUMMARY" /tmp/ng_br_edge_recheck_after_usdrub_block_v1.log
grep -q "trades_total=" /tmp/ng_br_edge_recheck_after_usdrub_block_v1.log
grep -q "net_pnl_total=" /tmp/ng_br_edge_recheck_after_usdrub_block_v1.log
grep -q "VERDICT=" /tmp/ng_br_edge_recheck_after_usdrub_block_v1.log
grep -q "db_update=0" /tmp/ng_br_edge_recheck_after_usdrub_block_v1.log

echo
echo "=== NG BR EDGE RECHECK SUMMARY ==="
grep -E "NG_BR_EDGE_RECHECK_ROW|trades_total=|gross_pnl_total=|commission_total=|net_pnl_total=|fee_drag_rows=|research_candidates=|VERDICT=" \
  /tmp/ng_br_edge_recheck_after_usdrub_block_v1.log

echo TEST_NG_BR_EDGE_RECHECK_AFTER_USDRUB_BLOCK_V1_OK
