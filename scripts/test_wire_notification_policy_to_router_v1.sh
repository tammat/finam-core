#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_WIRE_NOTIFICATION_POLICY_TO_ROUTER_V1_START"

TMP_LOG="$(mktemp)"

TELEGRAM_NOTIFY_DRY_RUN=1 python - <<'PY' 2>&1 | tee "$TMP_LOG"
from datetime import datetime, timezone

from finam_core.notifications.notification_policy_layer_v1 import NotificationPolicyLayerV1
from finam_core.notifications.notification_router_v1 import (
    NotificationEventV1,
    NotificationRouterV1,
)


class FixedPolicy(NotificationPolicyLayerV1):
    def __init__(self, now_utc):
        super().__init__(
            quiet_hours_enabled=True,
            quiet_hours_start=23,
            quiet_hours_end=7,
        )
        self._now_utc = now_utc

    def evaluate(self, *, severity: str, category: str, now_utc=None):
        return super().evaluate(
            severity=severity,
            category=category,
            now_utc=self._now_utc,
        )


router = NotificationRouterV1(
    policy_layer=FixedPolicy(datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)),
)

warning_event = NotificationEventV1(
    category="MANUAL_POSITION",
    severity="WARNING",
    symbol="BRN6@RTSX",
    title="⚠️ BRN6 SHORT REVIEW",
    body="Quiet hours suppression test.",
)

critical_event = NotificationEventV1(
    category="RISK",
    severity="CRITICAL",
    symbol="BRN6@RTSX",
    title="🚨 BRN6 CRITICAL RISK",
    body="Critical must pass policy.",
)

info_event = NotificationEventV1(
    category="ANALYTICS",
    severity="INFO",
    symbol="BRN6@RTSX",
    title="ℹ️ BRN6 INFO",
    body="Info must be aggregate only.",
)

warning_result = router.route(warning_event)
critical_result = router.route(critical_event)
info_result = router.route(info_event)

assert warning_result.accepted is True
assert warning_result.routed is False
assert warning_result.skipped_reason == "quiet_hours_warning_suppressed"

assert critical_result.accepted is True
assert critical_result.routed is True
assert critical_result.channel == "TELEGRAM"

assert info_result.accepted is True
assert info_result.routed is False
assert info_result.skipped_reason == "aggregate_only"

print("WIRE_NOTIFICATION_POLICY_TO_ROUTER_V1_PY_OK")
PY

grep -q "reason=quiet_hours_warning_suppressed" "$TMP_LOG"
grep -q "reason=aggregate_only" "$TMP_LOG"
grep -q "NOTIFICATION_ROUTER_ROUTE_OK" "$TMP_LOG"
grep -q "WIRE_NOTIFICATION_POLICY_TO_ROUTER_V1_PY_OK" "$TMP_LOG"

echo "TEST_WIRE_NOTIFICATION_POLICY_TO_ROUTER_V1_OK"
