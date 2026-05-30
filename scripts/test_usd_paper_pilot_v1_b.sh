#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_USD_PAPER_PILOT_V1_B_START"

python -m py_compile \
  src/finam_core/governance/usd_continuous_profile_gate_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "_usd_paper_pilot_profile_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "_usd_paper_pilot_allows_intent_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "ENABLE_USD_PAPER_PILOT_GATE_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "USD_PAPER_GOVERNANCE_ALLOWED" src/finam_core/pipelines/paper_pipeline.py
grep -q "USD_PAPER_GOVERNANCE_BLOCKED" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_USD_PAPER_PILOT_V1_B_OK"
