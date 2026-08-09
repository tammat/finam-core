#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST UNIVERSE READY SIGNAL SCREEN V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_ready_signal_screen_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_universe_ready_signal_screen_v1.py
)"

echo "$OUTPUT"

grep -q 'mode=gross_signal_screen' \
  <<< "$OUTPUT"

grep -q 'symbols=5' \
  <<< "$OUTPUT"

for symbol in \
  'USDRUBF@RTSX' \
  'NVTK@MISX' \
  'PLZL@MISX' \
  'VTBR@MISX' \
  'T@MISX'
do
    grep -q \
      "SYMBOL_ROW symbol=${symbol}" \
      <<< "$OUTPUT"
done

grep -q 'family=MOMENTUM' \
  <<< "$OUTPUT"

grep -q 'family=MEAN_REVERSION' \
  <<< "$OUTPUT"

grep -q 'family=BREAKOUT' \
  <<< "$OUTPUT"

grep -q 'gross_signal_edge_search=1' \
  <<< "$OUTPUT"

grep -q 'economic_edge_claimed=0' \
  <<< "$OUTPUT"

grep -q 'execution_instrument_used=0' \
  <<< "$OUTPUT"

grep -q 'execution_costs_used=0' \
  <<< "$OUTPUT"

grep -q 'purged_oos_used=1' \
  <<< "$OUTPUT"

grep -q 'db_writes_performed=0' \
  <<< "$OUTPUT"

grep -q 'runtime_changed=0' \
  <<< "$OUTPUT"

grep -q 'execution_changed=0' \
  <<< "$OUTPUT"

grep -q 'orders_changed=0' \
  <<< "$OUTPUT"

grep -q 'fills_changed=0' \
  <<< "$OUTPUT"

grep -q 'micro_live_allowed=0' \
  <<< "$OUTPUT"

grep -Eq \
'VERDICT=UNIVERSE_READY_SIGNAL_(CANDIDATES_FOUND|NO_CANDIDATES)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_UNIVERSE_READY_SIGNAL_SCREEN_V1_OK"
