#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST BR NEW STRATEGY FAMILY DISCOVERY V1 ==="

python -m py_compile \
  src/scripts/research/build_br_new_strategy_family_discovery_v1.py

OUTPUT="$(
    PYTHONPATH=src \
    python src/scripts/research/build_br_new_strategy_family_discovery_v1.py
)"

echo "$OUTPUT"

grep -q \
  'excluded_strategy=BR_CONSERVATIVE_BREAKOUT' \
  <<< "$OUTPUT"

grep -q \
  'families=MOMENTUM,MEAN_REVERSION' \
  <<< "$OUTPUT"

grep -q \
  'runtime_changed=0' \
  <<< "$OUTPUT"

grep -q \
  'execution_changed=0' \
  <<< "$OUTPUT"

grep -q \
  'db_writes_performed=0' \
  <<< "$OUTPUT"

grep -Eq \
  'VERDICT=BR_NEW_STRATEGY_FAMILY_DISCOVERY_(CANDIDATES_FOUND|NO_CANDIDATES)' \
  <<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "VERDICT=TEST_BR_NEW_STRATEGY_FAMILY_DISCOVERY_V1_OK"
