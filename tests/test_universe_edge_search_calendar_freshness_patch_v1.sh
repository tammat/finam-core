#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST UNIVERSE EDGE SEARCH CALENDAR FRESHNESS PATCH V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_edge_search_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_universe_edge_search_v1.py
)"

echo "$OUTPUT"

grep -q \
  'freshness_model=TRADING_CALENDAR_V1' \
  <<< "$OUTPUT"

grep -q \
  'global_universe_timestamp_used_for_gate=0' \
  <<< "$OUTPUT"

grep -q \
  'calendar_activity_ratio_used=1' \
  <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"

echo
echo "=== MOEX FALSE STALE GUARD ==="

for symbol in \
  'SBERP@MISX' \
  'VTBR@MISX' \
  'NVTK@MISX' \
  'T@MISX' \
  'SBER@MISX' \
  'LKOH@MISX' \
  'PLZL@MISX' \
  'IMOEX' \
  'RTSI'
do
    if grep -E \
      "symbol=${symbol} .*STALE_RELATIVE_TO_UNIVERSE" \
      <<< "$OUTPUT"
    then
        echo "ERROR=FALSE_CALENDAR_STALE symbol=${symbol}"
        exit 1
    fi
done

echo \
"VERDICT=UNIVERSE_EDGE_SEARCH_CALENDAR_FRESHNESS_REGRESSION_OK"

echo
echo "=== ETHUSD STALE GUARD ==="

if grep -E \
  'symbol=ETHUSD .*status=READY' \
  <<< "$OUTPUT"
then
    echo "ERROR=ETHUSD_FALSE_READY"
    exit 1
fi

echo "VERDICT=ETHUSD_STALE_GUARD_OK"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_UNIVERSE_EDGE_SEARCH_CALENDAR_FRESHNESS_PATCH_V1_OK"
