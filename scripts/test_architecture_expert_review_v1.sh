#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/architecture/build_architecture_expert_review_v1.py

python3 \
  src/scripts/architecture/build_architecture_expert_review_v1.py \
  | tee /tmp/architecture_expert_review_v1.log

grep -q "ARCHITECTURE EXPERT REVIEW V1" \
  /tmp/architecture_expert_review_v1.log

grep -q "ARCH_DB_VERDICT" \
  /tmp/architecture_expert_review_v1.log

grep -q "ARCH_PYTHON_VERDICT" \
  /tmp/architecture_expert_review_v1.log

grep -q "ARCH_ALGOTRADING_VERDICT" \
  /tmp/architecture_expert_review_v1.log

grep -q "ARCH_FINAL_VERDICT" \
  /tmp/architecture_expert_review_v1.log

grep -q "ARCHITECTURE_EXPERT_REVIEW_V1_OK" \
  /tmp/architecture_expert_review_v1.log

echo TEST_ARCHITECTURE_EXPERT_REVIEW_V1_OK
