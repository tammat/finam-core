#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_FAST_WINNER_PATTERN_DISCOVERY_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_fast_winner_pattern_discovery_v1.py

src/scripts/research/build_fast_winner_pattern_discovery_v1.py \
  | tee /tmp/fast_winner_pattern_discovery_v1.out

grep -q "FAST_WINNER_PATTERN_DISCOVERY_V1" /tmp/fast_winner_pattern_discovery_v1.out
grep -q "PATTERN_ROWS" /tmp/fast_winner_pattern_discovery_v1.out
grep -q "PATTERN_ROW section=CLASS pattern_class=FAST_WINNER" /tmp/fast_winner_pattern_discovery_v1.out
grep -q "PATTERN_ROW section=CLASS pattern_class=FAST_LOSER" /tmp/fast_winner_pattern_discovery_v1.out
grep -q "VERDICT=FAST_WINNER_PATTERN_DISCOVERY_READY" /tmp/fast_winner_pattern_discovery_v1.out

echo "TEST_FAST_WINNER_PATTERN_DISCOVERY_V1_OK"
