#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/seed_futures_regime_snapshots.py

grep -q "FUTURES_REGIME_SNAPSHOT_SUMMARY" src/scripts/seed_futures_regime_snapshots.py
grep -q "futures_contract_universe" src/scripts/seed_futures_regime_snapshots.py
grep -q "RegimeSnapshotRepository" src/scripts/seed_futures_regime_snapshots.py

echo "TEST_FUTURES_REGIME_SNAPSHOTS_OK"
