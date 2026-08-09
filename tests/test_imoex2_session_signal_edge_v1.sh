#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST IMOEX2 SESSION SIGNAL EDGE V1 ==="

python -m py_compile \
  src/scripts/research/build_imoex2_session_signal_edge_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_imoex2_session_signal_edge_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=gross_session_signal_edge_discovery' \
  <<< "$OUTPUT"

grep -q 'signal_symbol=IMOEX2' <<< "$OUTPUT"
grep -q 'session_timezone=Europe/Moscow' <<< "$OUTPUT"

grep -q 'code=MORNING' <<< "$OUTPUT"
grep -q 'code=MIDDAY' <<< "$OUTPUT"
grep -q 'code=AFTERNOON' <<< "$OUTPUT"
grep -q 'code=EVENING' <<< "$OUTPUT"

grep -q 'SESSION_DISCOVERY_ROW' <<< "$OUTPUT"

grep -q 'regime_conditioning_used=0' <<< "$OUTPUT"
grep -q 'execution_instrument_used=0' <<< "$OUTPUT"
grep -q 'execution_costs_used=0' <<< "$OUTPUT"
grep -q 'microstructure_used=0' <<< "$OUTPUT"

grep -q 'commission=0' <<< "$OUTPUT"
grep -q 'slippage=0' <<< "$OUTPUT"

grep -q \
  'gross_session_signal_edge_search=1' \
  <<< "$OUTPUT"

grep -q 'economic_edge_claimed=0' <<< "$OUTPUT"
grep -q 'multiple_testing_adjusted=1' <<< "$OUTPUT"
grep -q 'purged_oos_used=1' <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=IMOEX2_SESSION_SIGNAL_(CANDIDATES_FOUND|NO_CANDIDATES)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_IMOEX2_SESSION_SIGNAL_EDGE_V1_OK"
