#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/regime_guard_candidate_reader.py \
  src/scripts/runtime/test_regime_guard_candidate_reader_v1.py

python3 src/scripts/runtime/test_regime_guard_candidate_reader_v1.py | \
  tee /tmp/regime_guard_candidate_reader_v1.log

grep -q "REGIME GUARD CANDIDATE READER V1" /tmp/regime_guard_candidate_reader_v1.log
grep -q "ROWS_FOUND=" /tmp/regime_guard_candidate_reader_v1.log
grep -q "VERDICT=OK" /tmp/regime_guard_candidate_reader_v1.log

echo REGIME_GUARD_CANDIDATE_READER_V1_OK
