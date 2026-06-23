#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_UNTRACKED_CLASSIFICATION_V1 ==="

python3 -m py_compile src/scripts/research/build_research_untracked_classification_v1.py

out="/tmp/research_untracked_classification_v1.log"
python3 src/scripts/research/build_research_untracked_classification_v1.py | tee "$out"

grep -q "RESEARCH_UNTRACKED_CLASSIFICATION_V1" "$out"
grep -q "CLASSIFICATION_ROWS" "$out"
grep -q "KEEP_AND_COMMIT" "$out"
grep -q "REVIEW_BEFORE_COMMIT" "$out"
grep -q "VERDICT=RESEARCH_UNTRACKED_CLASSIFICATION_READY" "$out"

echo "TEST_RESEARCH_UNTRACKED_CLASSIFICATION_V1_OK"
