#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_identity_profile_candidate_v1.py

grep -q "BR_ASIA_SCALP_MEDIUM_MOVE" src/scripts/research/build_br_identity_profile_candidate_v1.py
grep -q "runtime_enabled=false" src/scripts/research/build_br_identity_profile_candidate_v1.py
grep -q "research_only=true" src/scripts/research/build_br_identity_profile_candidate_v1.py
grep -q "BR_IDENTITY_PROFILE_CANDIDATE_V1_OK" src/scripts/research/build_br_identity_profile_candidate_v1.py

echo "BR_IDENTITY_PROFILE_CANDIDATE_V1_TEST_OK"
