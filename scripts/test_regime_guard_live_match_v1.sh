#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_regime_guard_live_match_v1.py

python3 src/scripts/research/build_regime_guard_live_match_v1.py | \
  tee /tmp/regime_guard_live_match_v1.log

grep -q "REGIME GUARD LIVE MATCH V1" /tmp/regime_guard_live_match_v1.log
grep -q "ENERGY_USD_KEY=" /tmp/regime_guard_live_match_v1.log
grep -q "FULL_KEY=" /tmp/regime_guard_live_match_v1.log
grep -q "PIPE_REGIME_GUARD_ADVISORY" /tmp/regime_guard_live_match_v1.log
grep -q "actual_block=0" /tmp/regime_guard_live_match_v1.log
grep -q "advisory_only=1" /tmp/regime_guard_live_match_v1.log
grep -q "VERDICT=OK" /tmp/regime_guard_live_match_v1.log

echo REGIME_GUARD_LIVE_MATCH_V1_OK
