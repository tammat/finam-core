#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_WIRE_RISK_NOTIFICATION_BRIDGE_TO_AUDIT_STORAGE_V1_START"

TMP_LOG="$(mktemp)"

BEFORE_ID="$(psql "$DATABASE_URL" -At -c "select coalesce(max(id), 0) from risk_event_audit_v1;" 2>/dev/null || echo 0)"

TELEGRAM_NOTIFY_DRY_RUN=1 python - <<'PY' 2>&1 | tee "$TMP_LOG"
from datetime import datetime, timezone

from finam_core.notifications.notification_dispatch_service_v1 import (
    NotificationDispatchServiceV1,
)
from finam_core.notifications.notification_policy_layer_v1 import (
    NotificationPolicyLayerV1,
)
from finam_core.notifications.notification_router_v1 import NotificationRouterV1
from finam_core.notifications.risk_event_audit_storage_v1 import RiskEventAuditStorageV1
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
bridge = RiskNotificationBridgeV1(
    dispatcher=dispatcher,
    audit_storage=RiskEventAuditStorageV1(),
    audit_enabled=True,
)

risk_event = RiskNotificationInputV1(
    symbol="BRN6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    decision="REJECT",
    reason="wire_audit_storage_test",
    severity="CRITICAL",
    value=-2500.0,
    exposure=251000.0,
    risk_limit=1000.0,
    raw={
        "test": "wire_risk_notification_bridge_to_audit_storage_v1",
    },
)

result = bridge.dispatch_risk_event(risk_event)

assert result.accepted is True
assert result.routed is True
assert result.channel == "TELEGRAM"
assert result.category == "RISK"
assert result.severity == "CRITICAL"

print("WIRE_RISK_NOTIFICATION_BRIDGE_TO_AUDIT_STORAGE_V1_PY_OK")
PY

AFTER_ID="$(psql "$DATABASE_URL" -At -c "select coalesce(max(id), 0) from risk_event_audit_v1;")"

if [ "$AFTER_ID" -le "$BEFORE_ID" ]; then
  echo "RISK_EVENT_AUDIT_STORAGE_NO_NEW_ROW before=$BEFORE_ID after=$AFTER_ID"
  exit 1
fi

psql "$DATABASE_URL" -c "
select
  id,
  created_at,
  category,
  severity,
  symbol,
  strategy,
  timeframe,
  decision,
  reason,
  routed,
  channel,
  skipped_reason
from risk_event_audit_v1
where id = $AFTER_ID;
"

grep -q "NOTIFICATION_ROUTER_ROUTE_OK" "$TMP_LOG"
grep -q "NOTIFICATION_DISPATCH_RESULT" "$TMP_LOG"
grep -q "RISK_EVENT_AUDIT_STORAGE_INSERT_OK" "$TMP_LOG"
grep -q "RISK_NOTIFICATION_AUDIT_SAVED" "$TMP_LOG"
grep -q "WIRE_RISK_NOTIFICATION_BRIDGE_TO_AUDIT_STORAGE_V1_PY_OK" "$TMP_LOG"

echo "TEST_WIRE_RISK_NOTIFICATION_BRIDGE_TO_AUDIT_STORAGE_V1_OK"
