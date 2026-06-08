#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_ng_post_filter_scorecard_v2.py

python3 src/scripts/analytics/build_br_ng_post_filter_scorecard_v2.py \
  | tee /tmp/br_ng_post_filter_scorecard_v2.log

grep -q "BR NG POST FILTER SCORECARD V2" /tmp/br_ng_post_filter_scorecard_v2.log
grep -q "ROOT_ROW root=BR" /tmp/br_ng_post_filter_scorecard_v2.log
grep -q "ROOT_ROW root=NG" /tmp/br_ng_post_filter_scorecard_v2.log
grep -q "BR_NG_POST_FILTER_SCORECARD_V2_OK" /tmp/br_ng_post_filter_scorecard_v2.log

echo "TEST_BR_NG_POST_FILTER_SCORECARD_V2_OK"
