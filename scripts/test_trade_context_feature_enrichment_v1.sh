#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/features/enrich_trade_context_from_feature_snapshots.py

grep -q "feature_snapshots" src/scripts/features/enrich_trade_context_from_feature_snapshots.py
grep -q "trade_context_snapshots" src/scripts/features/enrich_trade_context_from_feature_snapshots.py
grep -q "TRADE_CONTEXT_FEATURE_ENRICHMENT_OK" src/scripts/features/enrich_trade_context_from_feature_snapshots.py
grep -q "fs.ts <= t.entry_ts" src/scripts/features/enrich_trade_context_from_feature_snapshots.py

echo "TRADE_CONTEXT_FEATURE_ENRICHMENT_V1_TEST_OK"
