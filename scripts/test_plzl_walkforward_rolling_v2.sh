#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_plzl_walkforward_rolling_v2.py

python3 src/scripts/research/build_plzl_walkforward_rolling_v2.py \
  | tee /tmp/plzl_walkforward_rolling_v2.log

grep -q "PLZL WALKFORWARD ROLLING V2" /tmp/plzl_walkforward_rolling_v2.log
grep -q "date_source=closed_trade_chains_v2.exit_ts" /tmp/plzl_walkforward_rolling_v2.log
grep -q "execution_enabled=0" /tmp/plzl_walkforward_rolling_v2.log
grep -q "PLZL_WF_SERIES" /tmp/plzl_walkforward_rolling_v2.log
grep -q "PLZL_WALKFORWARD_ROLLING_V2_SUMMARY" /tmp/plzl_walkforward_rolling_v2.log
grep -q "PLZL_WALKFORWARD_ROLLING_V2_OK" /tmp/plzl_walkforward_rolling_v2.log

echo TEST_PLZL_WALKFORWARD_ROLLING_V2_OK
