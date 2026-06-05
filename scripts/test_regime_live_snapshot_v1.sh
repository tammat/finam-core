#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_regime_live_snapshot_v1.py

python3 src/scripts/research/build_regime_live_snapshot_v1.py | \
  tee /tmp/regime_live_snapshot_v1.log

grep -q "REGIME LIVE SNAPSHOT V1" /tmp/regime_live_snapshot_v1.log
grep -q "LIVE_REGIME_KEY=" /tmp/regime_live_snapshot_v1.log
grep -q "VERDICT=OK" /tmp/regime_live_snapshot_v1.log

echo REGIME_LIVE_SNAPSHOT_V1_OK
