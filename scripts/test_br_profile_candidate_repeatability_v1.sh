#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_profile_candidate_repeatability_v1.py

grep -q "BR_ASIA_SCALP_MEDIUM_MOVE" src/scripts/research/build_br_profile_candidate_repeatability_v1.py
grep -q "DAY_MAP" src/scripts/research/build_br_profile_candidate_repeatability_v1.py
grep -q "REPEATABILITY_CONFIRMED" src/scripts/research/build_br_profile_candidate_repeatability_v1.py
grep -q "runtime_enabled=false" src/scripts/research/build_br_profile_candidate_repeatability_v1.py
grep -q "BR_PROFILE_CANDIDATE_REPEATABILITY_V1_OK" src/scripts/research/build_br_profile_candidate_repeatability_v1.py

echo "BR_PROFILE_CANDIDATE_REPEATABILITY_V1_TEST_OK"
