#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_lkoh_shadow_scorecard_v1.py

python3 src/scripts/research/build_lkoh_shadow_scorecard_v1.py \
  | tee /tmp/lkoh_shadow_scorecard_v1.log

grep -q "LKOH SHADOW SCORECARD V1" /tmp/lkoh_shadow_scorecard_v1.log
grep -q "SCORECARD_ROW" /tmp/lkoh_shadow_scorecard_v1.log
grep -q "runtime_allow=0" /tmp/lkoh_shadow_scorecard_v1.log
grep -q "execution_enabled=0" /tmp/lkoh_shadow_scorecard_v1.log
grep -q "LKOH_SHADOW_SCORECARD_V1_OK" /tmp/lkoh_shadow_scorecard_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
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
FROM lkoh_shadow_scorecard
ORDER BY id DESC
LIMIT 1;
" | tee /tmp/lkoh_shadow_scorecard_db_v1.log

grep -q "LKOH@MISX" /tmp/lkoh_shadow_scorecard_db_v1.log
grep -q "lkoh_shadow_signal_research_v1" /tmp/lkoh_shadow_scorecard_db_v1.log
grep -q " f " /tmp/lkoh_shadow_scorecard_db_v1.log

echo TEST_LKOH_SHADOW_SCORECARD_V1_OK
