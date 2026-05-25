#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_gap_toxicity_v2.py

grep -q "TINY_MOVE" src/scripts/research/build_br_gap_toxicity_v2.py
grep -q "EXTREME_MOVE" src/scripts/research/build_br_gap_toxicity_v2.py
grep -q "gap_proxy_v2_uses_close_to_prev_close_percent_move" src/scripts/research/build_br_gap_toxicity_v2.py
grep -q "BR_GAP_TOXICITY_V2_OK" src/scripts/research/build_br_gap_toxicity_v2.py

echo "BR_GAP_TOXICITY_V2_TEST_OK"
