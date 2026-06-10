#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_watch_instrument_shadow_candidates_v1.py

python3 \
  src/scripts/analytics/build_watch_instrument_shadow_candidates_v1.py \
  | tee /tmp/watch_instrument_shadow_candidates_v1.log

grep -q "WATCH INSTRUMENT SHADOW CANDIDATES V1" \
  /tmp/watch_instrument_shadow_candidates_v1.log

grep -q "symbol=USDRUBF@RTSX" \
  /tmp/watch_instrument_shadow_candidates_v1.log

grep -q "symbol=LKOH@MISX" \
  /tmp/watch_instrument_shadow_candidates_v1.log

grep -q "runtime_allow=0" \
  /tmp/watch_instrument_shadow_candidates_v1.log

grep -q "WATCH_INSTRUMENT_SHADOW_CANDIDATES_V1_OK" \
  /tmp/watch_instrument_shadow_candidates_v1.log

echo TEST_WATCH_INSTRUMENT_SHADOW_CANDIDATES_V1_OK
