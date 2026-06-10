#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_br_runtime_time_filter_revalidation_v1.py

python3 src/scripts/analytics/build_br_runtime_time_filter_revalidation_v1.py \
  | tee /tmp/br_runtime_time_filter_revalidation_v1.log

grep -q "BR RUNTIME TIME FILTER REVALIDATION V1" /tmp/br_runtime_time_filter_revalidation_v1.log
grep -q "VARIANT_ROWS" /tmp/br_runtime_time_filter_revalidation_v1.log
grep -q "VARIANT_ROW variant=ALL_BR" /tmp/br_runtime_time_filter_revalidation_v1.log
grep -q "BEST_VARIANT" /tmp/br_runtime_time_filter_revalidation_v1.log
grep -q "BR_RUNTIME_TIME_FILTER_REVALIDATION_V1_OK" /tmp/br_runtime_time_filter_revalidation_v1.log

echo "TEST_BR_RUNTIME_TIME_FILTER_REVALIDATION_V1_OK"
