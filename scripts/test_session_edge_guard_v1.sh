#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/session_edge_guard.py \
  src/scripts/build_session_edge_guard.py

grep -q "CREATE VIEW session_edge_guard_v1" \
  sql/create_session_edge_guard_v1.sql

grep -q "SESSION_EDGE_CONFIRMED" \
  sql/create_session_edge_guard_v1.sql

grep -q "analytics_only" \
  sql/create_session_edge_guard_v1.sql

python - <<'PY'
from finam_core.analytics.session_edge_guard import SessionEdgeGuard

guard = SessionEdgeGuard()

ok = guard.decide(
    session_bucket="europe_open",
    hour_utc=7,
    advisory_status="confirmed",
    advisory_reason="SESSION_EDGE_CONFIRMED",
)
assert ok.status == "confirmed"

bad = guard.decide(
    session_bucket="us_overlap",
    hour_utc=14,
    advisory_status="insufficient_data",
    advisory_reason="SESSION_EDGE_INSUFFICIENT_DATA",
)
assert bad.status == "insufficient_data"

print("SESSION_EDGE_GUARD_V1_UNIT_OK")
PY

echo "SESSION_EDGE_GUARD_V1_COMPILE_OK"
