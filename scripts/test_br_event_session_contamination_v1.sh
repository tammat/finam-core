#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_event_session_contamination_v1.py

grep -q "HIGH_CONTAMINATION" src/scripts/research/build_br_event_session_contamination_v1.py
grep -q "LOW_CONTAMINATION" src/scripts/research/build_br_event_session_contamination_v1.py
grep -q "BR_EVENT_SESSION_CONTAMINATION_V1_OK" src/scripts/research/build_br_event_session_contamination_v1.py

echo "BR_EVENT_SESSION_CONTAMINATION_V1_TEST_OK"
