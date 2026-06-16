#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_plzl_edge_decomposition_v1.py

python3 src/scripts/research/build_plzl_edge_decomposition_v1.py \
  | tee /tmp/plzl_edge_decomposition_v1.log

grep -q "PLZL EDGE DECOMPOSITION V1" /tmp/plzl_edge_decomposition_v1.log
grep -q "execution_enabled=0" /tmp/plzl_edge_decomposition_v1.log
grep -q "PLZL_EDGE_MONTH" /tmp/plzl_edge_decomposition_v1.log
grep -q "PLZL_EDGE_DECOMPOSITION_SUMMARY" /tmp/plzl_edge_decomposition_v1.log
grep -q "PLZL_EDGE_DECOMPOSITION_V1_OK" /tmp/plzl_edge_decomposition_v1.log

echo TEST_PLZL_EDGE_DECOMPOSITION_V1_OK
