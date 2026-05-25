#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_repeatability_gate_v1.py

grep -q "repeatability_confirmed" src/scripts/research/build_br_repeatability_gate_v1.py
grep -q "repeatability_high_day_concentration" src/scripts/research/build_br_repeatability_gate_v1.py
grep -q "BR_REPEATABILITY_GATE_V1_OK" src/scripts/research/build_br_repeatability_gate_v1.py

echo "BR_REPEATABILITY_GATE_V1_TEST_OK"
