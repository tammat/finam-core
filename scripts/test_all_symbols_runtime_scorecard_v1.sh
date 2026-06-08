#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
src/scripts/analytics/build_all_symbols_runtime_scorecard_v1.py

python3 \
src/scripts/analytics/build_all_symbols_runtime_scorecard_v1.py \
| tee /tmp/all_symbols_runtime_scorecard_v1.log

grep -q "SYMBOL_SCORECARD" \
/tmp/all_symbols_runtime_scorecard_v1.log

grep -q "ALL_SYMBOLS_RUNTIME_SCORECARD_V1_OK" \
/tmp/all_symbols_runtime_scorecard_v1.log

echo "TEST_ALL_SYMBOLS_RUNTIME_SCORECARD_V1_OK"
