#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_instrument_research_candidate_audit_v1.py

python3 \
  src/scripts/analytics/build_instrument_research_candidate_audit_v1.py \
  | tee /tmp/instrument_research_candidate_audit_v1.log

grep -q \
  "INSTRUMENT_RESEARCH_CANDIDATE_AUDIT_V1_OK" \
  /tmp/instrument_research_candidate_audit_v1.log

echo TEST_INSTRUMENT_RESEARCH_CANDIDATE_AUDIT_V1_OK
