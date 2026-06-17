#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST OPEN FORWARD CHAIN QTY RECONCILIATION V1 ==="

python3 -m py_compile src/scripts/research/build_open_forward_chain_qty_reconciliation_v1.py

python3 src/scripts/research/build_open_forward_chain_qty_reconciliation_v1.py \
  | tee /tmp/open_forward_chain_qty_reconciliation_v1.log

grep -q "OPEN_FORWARD_CHAIN_QTY_RECONCILIATION_V1_OK" /tmp/open_forward_chain_qty_reconciliation_v1.log
grep -q "QTY_RECON_TOTALS" /tmp/open_forward_chain_qty_reconciliation_v1.log
grep -q "VERDICT=" /tmp/open_forward_chain_qty_reconciliation_v1.log
grep -q "runtime_allow=0" /tmp/open_forward_chain_qty_reconciliation_v1.log
grep -q "execution_enabled=0" /tmp/open_forward_chain_qty_reconciliation_v1.log

echo TEST_OPEN_FORWARD_CHAIN_QTY_RECONCILIATION_V1_OK
