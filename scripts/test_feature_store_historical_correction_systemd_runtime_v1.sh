#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"

AUDIT_SERVICE="finam-feature-store-historical-correction-audit.service"
AUDIT_TIMER="finam-feature-store-historical-correction-audit.timer"
RETENTION_SERVICE="finam-feature-store-historical-correction-retention.service"
RETENTION_TIMER="finam-feature-store-historical-correction-retention.timer"

cd "$ROOT" || exit 1

echo "=== TEST_FEATURE_STORE_HISTORICAL_CORRECTION_SYSTEMD_RUNTIME_V1 ==="

for unit in \
    "$AUDIT_SERVICE" \
    "$AUDIT_TIMER" \
    "$RETENTION_SERVICE" \
    "$RETENTION_TIMER"
do
    systemctl cat "$unit" >/dev/null || {
        echo "ERROR=installed_unit_missing:$unit"
        exit 1
    }
done

systemctl is-enabled --quiet "$AUDIT_TIMER" || {
    echo "ERROR=audit_timer_not_enabled"
    exit 1
}

systemctl is-enabled --quiet "$RETENTION_TIMER" || {
    echo "ERROR=retention_timer_not_enabled"
    exit 1
}

systemctl is-active --quiet "$AUDIT_TIMER" || {
    echo "ERROR=audit_timer_not_active"
    exit 1
}

systemctl is-active --quiet "$RETENTION_TIMER" || {
    echo "ERROR=retention_timer_not_active"
    exit 1
}

STARTED_AT="$(
    date --iso-8601=seconds
)"

echo "validation_started_at=$STARTED_AT"

sudo systemctl start "$AUDIT_SERVICE"

systemctl is-failed --quiet "$AUDIT_SERVICE" && {
    echo "ERROR=audit_service_failed"
    exit 1
}

AUDIT_LOG="$(
    sudo journalctl \
        -u "$AUDIT_SERVICE" \
        --since "$STARTED_AT" \
        --no-pager
)"

grep -q \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1_READY" \
  <<<"$AUDIT_LOG" || {
    printf '%s\n' "$AUDIT_LOG"
    echo "ERROR=audit_service_verdict_missing"
    exit 1
}

grep -q "runtime_changed=0" <<<"$AUDIT_LOG"
grep -q "execution_changed=0" <<<"$AUDIT_LOG"
grep -q "orders_changed=0" <<<"$AUDIT_LOG"
grep -q "fills_changed=0" <<<"$AUDIT_LOG"
grep -q "micro_live_allowed=0" <<<"$AUDIT_LOG"

RETENTION_STARTED_AT="$(
    date --iso-8601=seconds
)"

sudo systemctl start "$RETENTION_SERVICE"

systemctl is-failed --quiet "$RETENTION_SERVICE" && {
    echo "ERROR=retention_service_failed"
    exit 1
}

RETENTION_LOG="$(
    sudo journalctl \
        -u "$RETENTION_SERVICE" \
        --since "$RETENTION_STARTED_AT" \
        --no-pager
)"

grep -q \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_RETENTION_V1_READY" \
  <<<"$RETENTION_LOG" || {
    printf '%s\n' "$RETENTION_LOG"
    echo "ERROR=retention_service_verdict_missing"
    exit 1
}

grep -q "dry_run=0" <<<"$RETENTION_LOG"
grep -q "runtime_changed=0" <<<"$RETENTION_LOG"
grep -q "execution_changed=0" <<<"$RETENTION_LOG"
grep -q "orders_changed=0" <<<"$RETENTION_LOG"
grep -q "fills_changed=0" <<<"$RETENTION_LOG"
grep -q "micro_live_allowed=0" <<<"$RETENTION_LOG"

FEATURE_STORE_TIMER_STATE="$(
    systemctl is-active finam-feature-store.timer
)"

[[ "$FEATURE_STORE_TIMER_STATE" == "active" ]] || {
    echo "ERROR=feature_store_timer_not_active"
    exit 1
}

AUDIT_NEXT="$(
    systemctl show "$AUDIT_TIMER" \
        -p NextElapseUSecRealtime \
        --value
)"

RETENTION_NEXT="$(
    systemctl show "$RETENTION_TIMER" \
        -p NextElapseUSecRealtime \
        --value
)"

echo "audit_service=SUCCESS"
echo "retention_service=SUCCESS"
echo "audit_timer=ACTIVE"
echo "retention_timer=ACTIVE"
echo "audit_next=$AUDIT_NEXT"
echo "retention_next=$RETENTION_NEXT"
echo "feature_store_timer=ACTIVE"
echo "feature_store_timer_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=TEST_FEATURE_STORE_HISTORICAL_CORRECTION_SYSTEMD_RUNTIME_V1_OK"
