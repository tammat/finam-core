#!/usr/bin/env bash
set -euo pipefail

python -m py_compile \
  src/finam_core/analytics/trade_context_snapshot_repository.py \
  src/scripts/build_trade_context_snapshots.py

grep -q "TRADE_CONTEXT_SNAPSHOTS_MIGRATE_SKIPPED" src/scripts/build_trade_context_snapshots.py
grep -q "repo.save(item)" src/scripts/build_trade_context_snapshots.py
grep -q "build_snapshots" src/scripts/build_trade_context_snapshots.py

echo "BUILD_TRADE_CONTEXT_SNAPSHOTS_WRITER_ONLY_TEST_OK"
