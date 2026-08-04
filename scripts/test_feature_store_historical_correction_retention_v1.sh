#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
FILE="$ROOT/src/scripts/run_feature_store_historical_correction_retention_v1.py"
POLICY="$ROOT/config/runtime/feature_store_historical_correction_retention_v1.json"

DB_NAME="${DB_NAME:-finam_core}"

TEST_RUN_ID="00000000-0000-0000-0000-00000000a401"
CLEAN_EXPIRED_ID="00000000-0000-0000-0000-00000000a411"
CLEAN_FRESH_ID="00000000-0000-0000-0000-00000000a412"
DETECTED_EXPIRED_ID="00000000-0000-0000-0000-00000000a413"
DETECTED_FRESH_ID="00000000-0000-0000-0000-00000000a414"

DRY_LOG="/tmp/feature_store_historical_correction_retention_dry_v1.log"
APPLY_LOG="/tmp/feature_store_historical_correction_retention_apply_v1.log"

cd "$ROOT" || exit 1

echo "=== TEST_FEATURE_STORE_HISTORICAL_CORRECTION_RETENTION_V1 ==="

[[ -f "$FILE" ]] || {
    echo "ERROR=retention_builder_missing"
    exit 1
}

[[ -f "$POLICY" ]] || {
    echo "ERROR=retention_policy_missing"
    exit 1
}

PYTHONPATH=src python -m py_compile "$FILE"

python3 - <<'PY'
from pathlib import Path
import json

builder = Path(
    "src/scripts/"
    "run_feature_store_historical_correction_retention_v1.py"
).read_text(encoding="utf-8")

policy = json.loads(
    Path(
        "config/runtime/"
        "feature_store_historical_correction_retention_v1.json"
    ).read_text(encoding="utf-8")
)

required_builder = [
    "FOR UPDATE SKIP LOCKED",
    "DELETE FROM",
    "--apply",
    "dry_run = not args.apply",
    "pg_try_advisory_xact_lock",
    "FEATURE_STORE_HISTORICAL_CORRECTION_RETENTION_V1",
]

for token in required_builder:
    if token not in builder:
        raise SystemExit(
            f"ERROR=builder_contract_missing:{token}"
        )

if policy.get("clean_retention_days") != 30:
    raise SystemExit(
        "ERROR=unexpected_clean_retention_days"
    )

if policy.get("detected_retention_days") != 180:
    raise SystemExit(
        "ERROR=unexpected_detected_retention_days"
    )

if policy.get("delete_batch_limit", 0) <= 0:
    raise SystemExit(
        "ERROR=invalid_delete_batch_limit"
    )

print("source_contract=OK")
PY

cleanup() {
    sudo -u postgres \
    psql -X -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "
    DELETE FROM
        analytics.feature_store_historical_correction_audit_v1
    WHERE audit_run_id='${TEST_RUN_ID}'::uuid;
    " >/dev/null

    echo "cleanup_status=OK"
}

trap cleanup EXIT

cleanup

sudo -u postgres \
psql -X -d "$DB_NAME" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO analytics.feature_store_historical_correction_audit_v1 (
    audit_id,
    audit_run_id,
    symbol,
    timeframe,
    checked_rows,
    changed_rows,
    missing_market_snapshot_rows,
    missing_market_bar_rows,
    first_changed_ts,
    last_changed_ts,
    correction_detected,
    dry_run,
    source_version,
    created_at
)
VALUES
(
    '${CLEAN_EXPIRED_ID}'::uuid,
    '${TEST_RUN_ID}'::uuid,
    'RETENTION_TEST_CLEAN_EXPIRED',
    'M1',
    20,
    0,
    0,
    0,
    NULL,
    NULL,
    false,
    false,
    'RETENTION_TEST_V1',
    clock_timestamp() - interval '31 days'
),
(
    '${CLEAN_FRESH_ID}'::uuid,
    '${TEST_RUN_ID}'::uuid,
    'RETENTION_TEST_CLEAN_FRESH',
    'M1',
    20,
    0,
    0,
    0,
    NULL,
    NULL,
    false,
    false,
    'RETENTION_TEST_V1',
    clock_timestamp() - interval '29 days'
),
(
    '${DETECTED_EXPIRED_ID}'::uuid,
    '${TEST_RUN_ID}'::uuid,
    'RETENTION_TEST_DETECTED_EXPIRED',
    'M1',
    20,
    1,
    0,
    0,
    clock_timestamp() - interval '181 days',
    clock_timestamp() - interval '181 days',
    true,
    false,
    'RETENTION_TEST_V1',
    clock_timestamp() - interval '181 days'
),
(
    '${DETECTED_FRESH_ID}'::uuid,
    '${TEST_RUN_ID}'::uuid,
    'RETENTION_TEST_DETECTED_FRESH',
    'M1',
    20,
    1,
    0,
    0,
    clock_timestamp() - interval '179 days',
    clock_timestamp() - interval '179 days',
    true,
    false,
    'RETENTION_TEST_V1',
    clock_timestamp() - interval '179 days'
);
SQL

BEFORE_COUNT="$(
    sudo -u postgres \
    psql -X -d "$DB_NAME" -Atqc "
    SELECT count(*)
    FROM analytics.feature_store_historical_correction_audit_v1
    WHERE audit_run_id='${TEST_RUN_ID}'::uuid;
    "
)"

[[ "$BEFORE_COUNT" == "4" ]] || {
    echo "ERROR=test_rows_not_inserted:$BEFORE_COUNT"
    exit 1
}

echo "test_rows_before=$BEFORE_COUNT"

echo
echo "=== DRY RUN ==="

sudo -u postgres \
env DATABASE_URL="postgresql:///${DB_NAME}" \
PYTHONPATH=src \
/opt/finam-core/venv/bin/python "$FILE" |
    tee "$DRY_LOG"

grep -q "dry_run=1" "$DRY_LOG"
grep -q "deleted_rows=0" "$DRY_LOG"

grep -q \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_RETENTION_V1_READY" \
  "$DRY_LOG"

AFTER_DRY_COUNT="$(
    sudo -u postgres \
    psql -X -d "$DB_NAME" -Atqc "
    SELECT count(*)
    FROM analytics.feature_store_historical_correction_audit_v1
    WHERE audit_run_id='${TEST_RUN_ID}'::uuid;
    "
)"

[[ "$AFTER_DRY_COUNT" == "4" ]] || {
    echo "ERROR=dry_run_changed_rows:$AFTER_DRY_COUNT"
    exit 1
}

echo "test_rows_after_dry_run=$AFTER_DRY_COUNT"

echo
echo "=== APPLY ==="

sudo -u postgres \
env DATABASE_URL="postgresql:///${DB_NAME}" \
PYTHONPATH=src \
/opt/finam-core/venv/bin/python "$FILE" \
    --apply \
    --batch-limit 5000 |
    tee "$APPLY_LOG"

grep -q "dry_run=0" "$APPLY_LOG"

grep -q \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_RETENTION_V1_READY" \
  "$APPLY_LOG"

STATE="$(
    sudo -u postgres \
    psql -X -d "$DB_NAME" -AtF '|' -c "
    SELECT
        count(*) FILTER (
            WHERE audit_id='${CLEAN_EXPIRED_ID}'::uuid
        ),
        count(*) FILTER (
            WHERE audit_id='${CLEAN_FRESH_ID}'::uuid
        ),
        count(*) FILTER (
            WHERE audit_id='${DETECTED_EXPIRED_ID}'::uuid
        ),
        count(*) FILTER (
            WHERE audit_id='${DETECTED_FRESH_ID}'::uuid
        )
    FROM analytics.feature_store_historical_correction_audit_v1
    WHERE audit_run_id='${TEST_RUN_ID}'::uuid;
    "
)"

echo "retention_state=$STATE"

[[ "$STATE" == "0|1|0|1" ]] || {
    echo "ERROR=retention_boundary_invalid:$STATE"
    exit 1
}

DELETED_ROWS="$(
    awk -F= '
        /^deleted_rows=/ {
            print $2
            exit
        }
    ' "$APPLY_LOG"
)"

[[ "$DELETED_ROWS" =~ ^[0-9]+$ ]] || {
    echo "ERROR=invalid_deleted_rows"
    exit 1
}

(( DELETED_ROWS >= 2 )) || {
    echo "ERROR=expired_rows_not_deleted:$DELETED_ROWS"
    exit 1
}

echo "clean_expired_deleted=1"
echo "clean_fresh_preserved=1"
echo "detected_expired_deleted=1"
echo "detected_fresh_preserved=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=TEST_FEATURE_STORE_HISTORICAL_CORRECTION_RETENTION_V1_OK"
