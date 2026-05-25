#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research/build_br_cluster_regime_persistence_v1.py

grep -q "PERSISTENCE_CONFIRMED" \
  src/scripts/research/build_br_cluster_regime_persistence_v1.py

grep -q "PERSISTENCE_WITH_DECAY" \
  src/scripts/research/build_br_cluster_regime_persistence_v1.py

grep -q "BR_CLUSTER_REGIME_PERSISTENCE_V1_OK" \
  src/scripts/research/build_br_cluster_regime_persistence_v1.py

echo "BR_CLUSTER_REGIME_PERSISTENCE_V1_TEST_OK"
