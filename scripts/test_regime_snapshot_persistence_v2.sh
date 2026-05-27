#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/regime_snapshot_repository.py \
  src/scripts/analytics/build_regime_snapshots_v2.py

grep -q "analytics_regime_snapshots_v2" src/finam_core/analytics/regime_snapshot_repository.py
grep -q "v_regime_snapshots_v2_ru" src/finam_core/analytics/regime_snapshot_repository.py
grep -q "v_regime_snapshots_v2_summary_ru" src/finam_core/analytics/regime_snapshot_repository.py
grep -q "feature_snapshots" src/scripts/analytics/build_regime_snapshots_v2.py
grep -q "Europe/Moscow" src/scripts/analytics/build_regime_snapshots_v2.py

python - <<'PY'
from scripts.analytics.build_regime_snapshots_v2 import _session_from_ts_msk

assert _session_from_ts_msk(8) == "morning"
assert _session_from_ts_msk(11) == "main_1"
assert _session_from_ts_msk(15) == "main_2"
assert _session_from_ts_msk(20) == "evening"

print("REGIME_SNAPSHOT_SESSION_UNIT_OK")
PY

echo "REGIME_SNAPSHOT_PERSISTENCE_V2_TEST_OK"
