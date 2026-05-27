#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/edge_validation_engine.py \
  src/scripts/analytics/build_regime_aware_edge_v1.py

grep -q "analytics_regime_aware_edge_v1" src/scripts/analytics/build_regime_aware_edge_v1.py
grep -q "v_regime_aware_edge_ru" src/scripts/analytics/build_regime_aware_edge_v1.py
grep -q "v_regime_aware_edge_summary_ru" src/scripts/analytics/build_regime_aware_edge_v1.py
grep -q "trade_context_envelopes" src/scripts/analytics/build_regime_aware_edge_v1.py
grep -q "Europe/Moscow" src/scripts/analytics/build_regime_aware_edge_v1.py

python - <<'PY'
from scripts.analytics.build_regime_aware_edge_v1 import _session_from_ts_msk

assert _session_from_ts_msk(8) == "morning"
assert _session_from_ts_msk(11) == "main_1"
assert _session_from_ts_msk(15) == "main_2"
assert _session_from_ts_msk(20) == "evening"

print("REGIME_AWARE_EDGE_SESSION_UNIT_OK")
PY

echo "REGIME_AWARE_EDGE_V1_TEST_OK"
