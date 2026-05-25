#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research/build_br_session_filtered_edge_v1.py

grep -q "NO_US_OPEN" \
  src/scripts/research/build_br_session_filtered_edge_v1.py

grep -q "ASIA_ONLY" \
  src/scripts/research/build_br_session_filtered_edge_v1.py

grep -q "EUROPE_ONLY" \
  src/scripts/research/build_br_session_filtered_edge_v1.py

grep -q "EDGE_SURVIVES_WITHOUT_US_OPEN" \
  src/scripts/research/build_br_session_filtered_edge_v1.py

grep -q "BR_SESSION_FILTERED_EDGE_V1_OK" \
  src/scripts/research/build_br_session_filtered_edge_v1.py

echo "BR_SESSION_FILTERED_EDGE_V1_TEST_OK"
