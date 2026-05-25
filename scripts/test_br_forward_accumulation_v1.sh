#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research/build_br_forward_accumulation_v1.py

grep -q "STATUS_CHANGED" \
  src/scripts/research/build_br_forward_accumulation_v1.py

grep -q "send_telegram" \
  src/scripts/research/build_br_forward_accumulation_v1.py

grep -q "RESEARCH_WATCH" \
  src/scripts/research/build_br_forward_accumulation_v1.py

grep -q "BR_FORWARD_ACCUMULATION_V1_OK" \
  src/scripts/research/build_br_forward_accumulation_v1.py

echo "BR_FORWARD_ACCUMULATION_V1_TEST_OK"
