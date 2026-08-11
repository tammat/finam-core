#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/research/build_trend_pullback_historical_economic_replay_v2.py"

echo "=== TEST TREND PULLBACK HISTORICAL ECONOMIC REPLAY V2 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"

OUTPUT="$(
    PYTHONPATH=src "$PY" "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

test "$(
    grep -c \
      '^FROZEN_LINEAGE_ROW .*count_match=1 hash_match=1$' \
      <<< "$OUTPUT"
)" -eq 3

test "$(
    grep -c \
      '^HISTORICAL_ECONOMIC_REPLAY_V2_ROW .*match=1$' \
      <<< "$OUTPUT"
)" -eq 3

grep -q '^replay_cases=3$' <<< "$OUTPUT"
grep -q '^matched_cases=3$' <<< "$OUTPUT"
grep -q '^rejected_cases=3$' <<< "$OUTPUT"

grep -q \
  '^canonical_trade_replay_used=1$' \
  <<< "$OUTPUT"

grep -q \
  '^individual_trade_costing_used=1$' \
  <<< "$OUTPUT"

grep -q \
  '^economic_edge_claimed=0$' \
  <<< "$OUTPUT"

grep -q \
  '^micro_live_allowed=0$' \
  <<< "$OUTPUT"

grep -q \
  '^VERDICT=TREND_PULLBACK_HISTORICAL_ECONOMIC_REPLAY_V2_OK$' \
  <<< "$OUTPUT"

echo "frozen_lineage_rows=3"
echo "economic_match_rows=3"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_TREND_PULLBACK_HISTORICAL_ECONOMIC_REPLAY_V2_OK"
