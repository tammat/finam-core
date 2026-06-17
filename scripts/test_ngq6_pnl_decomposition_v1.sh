#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST NGQ6 PNL DECOMPOSITION V1 ==="

python3 -m py_compile src/scripts/research/build_ngq6_pnl_decomposition_v1.py

python3 src/scripts/research/build_ngq6_pnl_decomposition_v1.py \
  | tee /tmp/ngq6_pnl_decomposition_v1.log

grep -q "NGQ6_PNL_DECOMPOSITION_V1_OK" /tmp/ngq6_pnl_decomposition_v1.log
grep -q "VERDICT=PNL_NEGATIVE_BECAUSE_FIRST_FORWARD_CHAIN_LOST" /tmp/ngq6_pnl_decomposition_v1.log
grep -q "entry_trade_id=30374" /tmp/ngq6_pnl_decomposition_v1.log
grep -q "exit_trade_id=30379" /tmp/ngq6_pnl_decomposition_v1.log
grep -q "runtime_allow=0" /tmp/ngq6_pnl_decomposition_v1.log
grep -q "execution_enabled=0" /tmp/ngq6_pnl_decomposition_v1.log

echo TEST_NGQ6_PNL_DECOMPOSITION_V1_OK
