#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/analytics/build_trade_context_envelopes.py

grep -q "analytics_regime_snapshots_v2" src/scripts/analytics/build_trade_context_envelopes.py
grep -q "_nearest_regime_snapshot" src/scripts/analytics/build_trade_context_envelopes.py

if grep -q '_latest_json(conn, "futures_mtf_regime"' src/scripts/analytics/build_trade_context_envelopes.py; then
  echo "ERROR: old futures_mtf_regime fallback still used as primary regime source"
  exit 1
fi

echo "TRADE_CONTEXT_ENVELOPE_REGIME_SNAPSHOT_V2_TEST_OK"
