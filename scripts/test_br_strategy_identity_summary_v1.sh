#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_strategy_identity_summary_v1.py

grep -q "DECISION_SUMMARY" src/scripts/research/build_br_strategy_identity_summary_v1.py
grep -q "TOP_REASONS" src/scripts/research/build_br_strategy_identity_summary_v1.py
grep -q "TOP_COMBINATIONS" src/scripts/research/build_br_strategy_identity_summary_v1.py
grep -q "BR_STRATEGY_IDENTITY_SUMMARY_V1_OK" src/scripts/research/build_br_strategy_identity_summary_v1.py

echo "BR_STRATEGY_IDENTITY_SUMMARY_V1_TEST_OK"
