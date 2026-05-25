#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_cluster_walkforward_v1.py

grep -q "LOW_IMPULSE" src/scripts/research/build_br_cluster_walkforward_v1.py
grep -q "TRAIN_70" src/scripts/research/build_br_cluster_walkforward_v1.py
grep -q "TEST_30" src/scripts/research/build_br_cluster_walkforward_v1.py
grep -q "BR_CLUSTER_WALKFORWARD_V1_OK" src/scripts/research/build_br_cluster_walkforward_v1.py

echo "BR_CLUSTER_WALKFORWARD_V1_TEST_OK"
