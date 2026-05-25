#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_strategy_identity_guard_v1.py

grep -q "IDENTITY_RESEARCH_ONLY_REPEATABILITY_NOT_CONFIRMED" src/scripts/research/build_br_strategy_identity_guard_v1.py
grep -q "SCALP_LT_5M" src/scripts/research/build_br_strategy_identity_guard_v1.py
grep -q "MEDIUM_MOVE" src/scripts/research/build_br_strategy_identity_guard_v1.py
grep -q "blocked_session" src/scripts/research/build_br_strategy_identity_guard_v1.py
grep -q "BR_STRATEGY_IDENTITY_GUARD_V1_OK" src/scripts/research/build_br_strategy_identity_guard_v1.py

echo "BR_STRATEGY_IDENTITY_GUARD_V1_TEST_OK"
