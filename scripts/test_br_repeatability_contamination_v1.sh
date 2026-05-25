#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_repeatability_contamination_v1.py

grep -q "CORE_SCALP_ASIA" src/scripts/research/build_br_repeatability_contamination_v1.py
grep -q "DAY_MAP_CORE_SCALP_ASIA" src/scripts/research/build_br_repeatability_contamination_v1.py
grep -q "HIGH_DAY_CONCENTRATION" src/scripts/research/build_br_repeatability_contamination_v1.py
grep -q "BR_REPEATABILITY_CONTAMINATION_V1_OK" src/scripts/research/build_br_repeatability_contamination_v1.py

echo "BR_REPEATABILITY_CONTAMINATION_V1_TEST_OK"
