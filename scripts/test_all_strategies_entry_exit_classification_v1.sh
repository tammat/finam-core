#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST ALL STRATEGIES ENTRY EXIT CLASSIFICATION V1 ==="

python3 -m py_compile src/scripts/research/build_all_strategies_entry_exit_classification_v1.py

python3 src/scripts/research/build_all_strategies_entry_exit_classification_v1.py \
  | tee /tmp/all_strategies_entry_exit_classification_v1.log

grep -q "ALL_STRATEGIES_ENTRY_EXIT_CLASSIFICATION_V1_OK" /tmp/all_strategies_entry_exit_classification_v1.log
grep -q "CLASSIFICATION_SUMMARY" /tmp/all_strategies_entry_exit_classification_v1.log
grep -q "VERDICT=CLASSIFICATION_READY" /tmp/all_strategies_entry_exit_classification_v1.log
grep -q "runtime_allow=0" /tmp/all_strategies_entry_exit_classification_v1.log
grep -q "execution_enabled=0" /tmp/all_strategies_entry_exit_classification_v1.log

echo TEST_ALL_STRATEGIES_ENTRY_EXIT_CLASSIFICATION_V1_OK
