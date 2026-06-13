#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_lkoh_sell_only_scorecard_v1.py

python3 src/scripts/research/build_lkoh_sell_only_scorecard_v1.py \
  | tee /tmp/lkoh_sell_only_scorecard_v1.log

grep -q "LKOH SELL ONLY SCORECARD V1" /tmp/lkoh_sell_only_scorecard_v1.log
grep -q "SELL_ONLY_ROW" /tmp/lkoh_sell_only_scorecard_v1.log
grep -q "runtime_allow=0" /tmp/lkoh_sell_only_scorecard_v1.log
grep -q "execution_enabled=0" /tmp/lkoh_sell_only_scorecard_v1.log
grep -q "LKOH_SELL_ONLY_SCORECARD_V1_OK" /tmp/lkoh_sell_only_scorecard_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    source_strategy,
    strategy,
    exit_bars,
    signals,
    closed_trades,
    winrate,
    expectancy,
    profit_factor,
    verdict,
    runtime_allowed,
    execution_enabled
FROM lkoh_sell_only_scorecard
ORDER BY id DESC
LIMIT 1;
" | tee /tmp/lkoh_sell_only_scorecard_db_v1.log

grep -q "LKOH@MISX" /tmp/lkoh_sell_only_scorecard_db_v1.log
grep -q "lkoh_sell_only_scorecard_v1" /tmp/lkoh_sell_only_scorecard_db_v1.log
grep -q " f " /tmp/lkoh_sell_only_scorecard_db_v1.log

echo TEST_LKOH_SELL_ONLY_SCORECARD_V1_OK
