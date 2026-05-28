#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_NOTIFICATION_DISPATCH_SERVICE_V1_START"

TMP_LOG="$(mktemp)"

TELEGRAM_NOTIFY_DRY_RUN=1 python - <<'PY' 2>&1 | tee "$TMP_LOG"
from datetime import datetime, timezone

from finam_core.notifications.notification_dispatch_service_v1 import (
    NotificationDispatchServiceV1,
)
from finam_core.notifications.notification_policy_layer_v1 import (
    NotificationPolicyLayerV1,
)
from finam_core.notifications.notification_router_v1 import (
    NotificationEventV1,
    NotificationRouterV1,
)


class FixedPolicy(NotificationPolicyLayerV1):
    def evaluate(self, *, severity: str, category: str, now_utc=None):
        return super().evaluate(
            severity=severity,
            category=category,
            now_utc=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        )


router = NotificationRouterV1(
    policy_layer=FixedPolicy(
        quiet_hours_enabled=True,
        quiet_hours_start=23,
        quiet_hours_end=7,
    )
)

dispatcher = NotificationDispatchServiceV1(router=router)

event = NotificationEventV1(
    category="MANUAL_POSITION",
    severity="WARNING",
    symbol="BRN6@RTSX",
    title="⚠️ BRN6 SHORT REVIEW",
    body="Проверка dispatch service.",
)

result = dispatcher.dispatch(event)

assert result.accepted is True
assert result.routed is True
assert result.channel == "TELEGRAM"
assert result.severity == "WARNING"
assert result.symbol == "BRN6@RTSX"
assert result.category == "MANUAL_POSITION"

print("NOTIFICATION_DISPATCH_SERVICE_V1_PY_OK")
PY

grep -q "NOTIFICATION_ROUTER_ROUTE_OK" "$TMP_LOG"
grep -q "TELEGRAM_NOTIFY_DRY_RUN" "$TMP_LOG"
grep -q "NOTIFICATION_DISPATCH_RESULT" "$TMP_LOG"
grep -q "NOTIFICATION_DISPATCH_SERVICE_V1_PY_OK" "$TMP_LOG"

echo "TEST_NOTIFICATION_DISPATCH_SERVICE_V1_OK"
