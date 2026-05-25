#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research/build_br_intraday_temporal_stability_v1.py

grep -q "HOUR_MAP" \
  src/scripts/research/build_br_intraday_temporal_stability_v1.py

grep -q "SESSION_MAP" \
  src/scripts/research/build_br_intraday_temporal_stability_v1.py

grep -q "US_OPEN_TOXIC" \
  src/scripts/research/build_br_intraday_temporal_stability_v1.py

grep -q "TEMPORAL_EDGE_CONFIRMED_EX_US_OPEN" \
  src/scripts/research/build_br_intraday_temporal_stability_v1.py

grep -q "BR_INTRADAY_TEMPORAL_STABILITY_V1_OK" \
  src/scripts/research/build_br_intraday_temporal_stability_v1.py

echo "BR_INTRADAY_TEMPORAL_STABILITY_V1_TEST_OK"
