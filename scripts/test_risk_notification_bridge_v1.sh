#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RISK_NOTIFICATION_BRIDGE_V1_START"

TMP_LOG="$(mktemp)"

TELEGRAM_NOTIFY_DRY_RUN=1 python - <<'PY' 2>&1 | tee "$TMP_LOG"
from datetime import datetime, timezone

from finam_core.notifications.notification_dispatch_service_v1 import (
    NotificationDispatchServiceV1,
)
from finam_core.notifications.notification_policy_layer_v1 import (
    NotificationPolicyLayerV1,
)
from finam_core.notifications.notification_router_v1 import NotificationRouterV1
from finam_core.notifications.risk_notification_bridge_v1 import (
    RiskNotificationBridgeV1,
    RiskNotificationInputV1,
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
bridge = RiskNotificationBridgeV1(dispatcher=dispatcher)

risk_event = RiskNotificationInputV1(
    symbol="BRN6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    decision="REJECT",
    reason="daily_loss_limit",
    severity="CRITICAL",
    value=-1500.0,
    exposure=250000.0,
    risk_limit=1000.0,
)

notification_event = bridge.to_notification_event(risk_event)

assert notification_event.category == "RISK"
assert notification_event.severity == "CRITICAL"
assert notification_event.symbol == "BRN6@RTSX"
assert "daily_loss_limit" in notification_event.body

result = bridge.dispatch_risk_event(risk_event)

assert result.accepted is True
assert result.routed is True
assert result.channel == "TELEGRAM"
assert result.severity == "CRITICAL"
assert result.category == "RISK"

print("RISK_NOTIFICATION_BRIDGE_V1_PY_OK")
PY

grep -q "NOTIFICATION_ROUTER_ROUTE_OK" "$TMP_LOG"
grep -q "TELEGRAM_NOTIFY_DRY_RUN" "$TMP_LOG"
grep -q "NOTIFICATION_DISPATCH_RESULT" "$TMP_LOG"
grep -q "RISK_NOTIFICATION_BRIDGE_V1_PY_OK" "$TMP_LOG"

echo "TEST_RISK_NOTIFICATION_BRIDGE_V1_OK"
