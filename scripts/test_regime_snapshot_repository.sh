#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/regime_snapshot_repository.py \
  src/scripts/build_regime_snapshots.py

grep -q "regime_snapshots" src/finam_core/analytics/regime_snapshot_repository.py
grep -q "REGIME_SNAPSHOT_OK" src/scripts/build_regime_snapshots.py

echo "TEST_REGIME_SNAPSHOT_REPOSITORY_OK"
