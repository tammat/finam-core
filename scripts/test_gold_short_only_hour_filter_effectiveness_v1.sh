#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
src/scripts/research/build_gold_short_only_hour_filter_effectiveness_v1.py

python3 \
src/scripts/research/build_gold_short_only_hour_filter_effectiveness_v1.py \
| tee /tmp/gold_short_only_hour_filter_effectiveness_v1.log

grep -q "GOLD SHORT ONLY HOUR FILTER EFFECTIVENESS V1" \
/tmp/gold_short_only_hour_filter_effectiveness_v1.log

grep -q "VARIANT_ROW" \
/tmp/gold_short_only_hour_filter_effectiveness_v1.log

grep -q "BEST_VARIANT" \
/tmp/gold_short_only_hour_filter_effectiveness_v1.log

grep -q "GOLD_SHORT_ONLY_HOUR_FILTER_EFFECTIVENESS_V1_OK" \
/tmp/gold_short_only_hour_filter_effectiveness_v1.log

echo TEST_GOLD_SHORT_ONLY_HOUR_FILTER_EFFECTIVENESS_V1_OK
