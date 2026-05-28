#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_NOTIFICATION_ROUTER_V1_START"

TMP_LOG="$(mktemp)"

TELEGRAM_NOTIFY_DRY_RUN=1 python - <<'PY' 2>&1 | tee "$TMP_LOG"
from finam_core.notifications.notification_router_v1 import (
    NotificationEventV1,
    NotificationRouterV1,
)
from finam_core.notifications.notification_dedup_cache_v1 import NotificationDedupCacheV1

router = NotificationRouterV1(
    quiet_mode=False,
    dedup_cache=NotificationDedupCacheV1(
        cooldowns={
            "WARNING": 300.0,
        }
    ),
)

event = NotificationEventV1(
    category="MANUAL_POSITION",
    severity="WARNING",
    symbol="BRN6@RTSX",
    title="⚠️ BRN6 SHORT REVIEW",
    body="Требуется контроль позиции.",
)

first = router.route(event)
second = router.route(event)

assert first.accepted is True
assert first.routed is True
assert first.channel == "TELEGRAM"

assert second.accepted is True
assert second.routed is False
assert second.skipped_reason == "dedup_cooldown_active"

print("NOTIFICATION_ROUTER_V1_PY_OK")
PY

grep -q "NOTIFICATION_ROUTER_ROUTE_OK" "$TMP_LOG"
grep -q "TELEGRAM_NOTIFY_DRY_RUN" "$TMP_LOG"
grep -q "reason=dedup_cooldown_active" "$TMP_LOG"
grep -q "NOTIFICATION_ROUTER_V1_PY_OK" "$TMP_LOG"

echo "TEST_NOTIFICATION_ROUTER_V1_OK"
