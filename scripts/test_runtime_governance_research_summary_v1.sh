#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_governance_research_summary_v1.py

python3 \
  src/scripts/analytics/build_runtime_governance_research_summary_v1.py \
  | tee /tmp/runtime_governance_research_summary_v1.log

grep -q "RUNTIME GOVERNANCE RESEARCH SUMMARY V1" \
  /tmp/runtime_governance_research_summary_v1.log

grep -q "decision=WATCH_ONLY" \
  /tmp/runtime_governance_research_summary_v1.log

grep -q "runtime_promotion=NO" \
  /tmp/runtime_governance_research_summary_v1.log

grep -q "VERDICT=RUNTIME_GOVERNANCE_RESEARCH_SUMMARY_WATCH_ONLY" \
  /tmp/runtime_governance_research_summary_v1.log

grep -q "RUNTIME_GOVERNANCE_RESEARCH_SUMMARY_V1_OK" \
  /tmp/runtime_governance_research_summary_v1.log

echo TEST_RUNTIME_GOVERNANCE_RESEARCH_SUMMARY_V1_OK
