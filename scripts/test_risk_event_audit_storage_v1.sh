#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RISK_EVENT_AUDIT_STORAGE_V1_START"

TMP_LOG="$(mktemp)"

python - <<'PY' 2>&1 | tee "$TMP_LOG"
from finam_core.notifications.risk_event_audit_storage_v1 import (
    RiskEventAuditRecordV1,
    RiskEventAuditStorageV1,
)

storage = RiskEventAuditStorageV1()
storage.ensure_schema()

inserted_id = storage.insert_event(
    RiskEventAuditRecordV1(
        category="RISK",
        severity="CRITICAL",
        symbol="BRN6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        timeframe="M5",
        decision="REJECT",
        reason="daily_loss_limit",
        value=-1500.0,
        exposure=250000.0,
        risk_limit=1000.0,
        routed=True,
        channel="TELEGRAM",
        skipped_reason=None,
        raw={
            "source": "test",
            "pipeline": "risk_notification_bridge_v1",
        },
    )
)

assert inserted_id > 0

print("RISK_EVENT_AUDIT_STORAGE_V1_PY_OK", f"id={inserted_id}")
PY

grep -q "RISK_EVENT_AUDIT_STORAGE_SCHEMA_OK" "$TMP_LOG"
grep -q "RISK_EVENT_AUDIT_STORAGE_INSERT_OK" "$TMP_LOG"
grep -q "RISK_EVENT_AUDIT_STORAGE_V1_PY_OK" "$TMP_LOG"

echo "TEST_RISK_EVENT_AUDIT_STORAGE_V1_OK"
