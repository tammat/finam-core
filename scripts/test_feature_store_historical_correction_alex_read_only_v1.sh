#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"

echo "=== TEST_FEATURE_STORE_HISTORICAL_CORRECTION_ALEX_READ_ONLY_V1 ==="

READ_OK="$(
    psql -X -d "$DB_NAME" -Atqc "
    SELECT count(*) >= 0
    FROM analytics.feature_store_historical_correction_audit_v1;
    "
)"

[[ "$READ_OK" == "t" ]] || {
    echo "ERROR=alex_read_failed"
    exit 1
}

set +e

UPDATE_OUTPUT="$(
    psql -X -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "
    UPDATE analytics.feature_store_watermark_v1
    SET updated_at=updated_at
    WHERE false;
    " 2>&1
)"

UPDATE_RC=$?

set -e

[[ "$UPDATE_RC" -ne 0 ]] || {
    echo "ERROR=alex_update_unexpectedly_allowed"
    exit 1
}

grep -qiE \
  'permission denied|нет доступа' \
  <<<"$UPDATE_OUTPUT" || {
    echo "ERROR=unexpected_update_failure:$UPDATE_OUTPUT"
    exit 1
}

echo "alex_select=1"
echo "alex_update=0"
echo "owner_boundary=postgres"
echo \
  "VERDICT=TEST_FEATURE_STORE_HISTORICAL_CORRECTION_ALEX_READ_ONLY_V1_OK"
