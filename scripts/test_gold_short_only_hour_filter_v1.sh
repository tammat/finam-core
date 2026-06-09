#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
src/scripts/research/build_gold_short_only_hour_filter_v1.py

python3 \
src/scripts/research/build_gold_short_only_hour_filter_v1.py \
| tee /tmp/gold_short_only_hour_filter_v1.log

grep -q "GOLD SHORT ONLY HOUR FILTER V1" \
/tmp/gold_short_only_hour_filter_v1.log

grep -q "HOUR_FILTER_ROW" \
/tmp/gold_short_only_hour_filter_v1.log

grep -q "GOLD_SHORT_ONLY_HOUR_FILTER_V1_OK" \
/tmp/gold_short_only_hour_filter_v1.log

echo TEST_GOLD_SHORT_ONLY_HOUR_FILTER_V1_OK
