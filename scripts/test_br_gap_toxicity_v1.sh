#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_gap_toxicity_v1.py

grep -q "NO_OR_TINY_GAP" src/scripts/research/build_br_gap_toxicity_v1.py
grep -q "EXTREME_GAP" src/scripts/research/build_br_gap_toxicity_v1.py
grep -q "gap_proxy_uses_feature_snapshots" src/scripts/research/build_br_gap_toxicity_v1.py
grep -q "BR_GAP_TOXICITY_V1_OK" src/scripts/research/build_br_gap_toxicity_v1.py

echo "BR_GAP_TOXICITY_V1_TEST_OK"
