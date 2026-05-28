#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_NOTIFICATION_DEDUP_CACHE_V1_START"

python - <<'PY'
from finam_core.notifications.notification_dedup_cache_v1 import NotificationDedupCacheV1

cache = NotificationDedupCacheV1(
    cooldowns={
        "WARNING": 300.0,
        "CRITICAL": 0.0,
    }
)

first = cache.allows(
    category="MANUAL_POSITION",
    severity="WARNING",
    symbol="BRN6@RTSX",
    title="BRN6 SHORT REVIEW",
    now_ts=1000.0,
)

second = cache.allows(
    category="MANUAL_POSITION",
    severity="WARNING",
    symbol="BRN6@RTSX",
    title="BRN6 SHORT REVIEW",
    now_ts=1100.0,
)

third = cache.allows(
    category="MANUAL_POSITION",
    severity="WARNING",
    symbol="BRN6@RTSX",
    title="BRN6 SHORT REVIEW",
    now_ts=1401.0,
)

critical = cache.allows(
    category="RISK",
    severity="CRITICAL",
    symbol="BRN6@RTSX",
    title="CRITICAL RISK",
    now_ts=1500.0,
)

assert first.allowed is True
assert first.reason == "first_seen"

assert second.allowed is False
assert second.reason == "dedup_cooldown_active"

assert third.allowed is True
assert third.reason == "cooldown_elapsed"

assert critical.allowed is True
assert critical.reason == "bypass_cooldown"

print("NOTIFICATION_DEDUP_CACHE_V1_PY_OK")
PY

echo "TEST_NOTIFICATION_DEDUP_CACHE_V1_OK"
