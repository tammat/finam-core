#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_NOTIFICATION_POLICY_LAYER_V1_START"

python - <<'PY'
from datetime import datetime, timezone

from finam_core.notifications.notification_policy_layer_v1 import (
    NotificationPolicyLayerV1,
)

policy = NotificationPolicyLayerV1(
    quiet_hours_enabled=True,
    quiet_hours_start=23,
    quiet_hours_end=7,
)

critical = policy.evaluate(
    severity="CRITICAL",
    category="RISK",
    now_utc=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
)

warning = policy.evaluate(
    severity="WARNING",
    category="MANUAL_POSITION",
    now_utc=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
)

info = policy.evaluate(
    severity="INFO",
    category="ANALYTICS",
    now_utc=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
)

assert critical.allowed is True
assert critical.reason == "critical_always_allowed"

assert warning.allowed is False
assert warning.reason == "quiet_hours_warning_suppressed"

assert info.allowed is False
assert info.aggregate_only is True

print("NOTIFICATION_POLICY_LAYER_V1_PY_OK")
PY

echo "TEST_NOTIFICATION_POLICY_LAYER_V1_OK"
