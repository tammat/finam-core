#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/guard_candidate_classification_reader.py \
  src/scripts/runtime/test_guard_candidate_classification_reader_v1.py

python3 src/scripts/runtime/test_guard_candidate_classification_reader_v1.py | tee /tmp/guard_candidate_classification_reader_v1.log

grep -q "VERDICT=OK" /tmp/guard_candidate_classification_reader_v1.log
grep -q "ROWS_FOUND=" /tmp/guard_candidate_classification_reader_v1.log
grep -q "BLOCK_READY_FOUND=" /tmp/guard_candidate_classification_reader_v1.log
grep -q "SAMPLE" /tmp/guard_candidate_classification_reader_v1.log

echo GUARD_CANDIDATE_CLASSIFICATION_READER_V1_OK
