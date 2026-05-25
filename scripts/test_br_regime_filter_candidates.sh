#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_regime_filter_candidates.py

grep -q "KEEP_RESEARCH_CLUSTER" src/scripts/research/build_br_regime_filter_candidates.py
grep -q "DOWNWEIGHT_LOW_SAMPLE" src/scripts/research/build_br_regime_filter_candidates.py
grep -q "BLOCK_CLUSTER" src/scripts/research/build_br_regime_filter_candidates.py
grep -q "BR_REGIME_FILTER_CANDIDATES_V1_OK" src/scripts/research/build_br_regime_filter_candidates.py

echo "BR_REGIME_FILTER_CANDIDATES_V1_TEST_OK"
