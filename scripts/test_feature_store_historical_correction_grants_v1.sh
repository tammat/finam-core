#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
SQL_FILE="$ROOT/sql/analytics/015_feature_store_historical_correction_grants_v1.sql"
DB_NAME="${DB_NAME:-finam_core}"

cd "$ROOT" || exit 1

echo "=== TEST_FEATURE_STORE_HISTORICAL_CORRECTION_GRANTS_V1 ==="

[[ -f "$SQL_FILE" ]] || {
    echo "ERROR=grant_migration_missing"
    exit 1
}

bash -n \
  scripts/migrate_feature_store_historical_correction_grants_v1.sh

python3 - <<'PY'
from pathlib import Path

sql = Path(
    "sql/analytics/"
    "015_feature_store_historical_correction_grants_v1.sql"
).read_text(encoding="utf-8")

required = [
    "REVOKE ALL",
    "FROM PUBLIC",
    "GRANT USAGE",
    "TO finam",
    "GRANT SELECT, INSERT",
    "GRANT SELECT, UPDATE",
    "TO alex",
    "GRANT SELECT",
    "COMMIT;",
]

for token in required:
    if token not in sql:
        raise SystemExit(
            f"ERROR=grant_contract_missing:{token}"
        )

for forbidden in (
    "GRANT DELETE",
    "GRANT TRUNCATE",
    "GRANT REFERENCES",
    "GRANT TRIGGER",
    "GRANT ALL",
):
    if forbidden in sql:
        raise SystemExit(
            f"ERROR=excessive_grant_present:{forbidden}"
        )

print("source_contract=OK")
PY

FINAM_STATE="$(
    sudo -u postgres \
    psql -X -d "$DB_NAME" -AtF '|' -c "
    SELECT
        has_schema_privilege(
            'finam',
            'analytics',
            'USAGE'
        )::int,
        has_table_privilege(
            'finam',
            'analytics.feature_store_historical_correction_audit_v1',
            'SELECT'
        )::int,
        has_table_privilege(
            'finam',
            'analytics.feature_store_historical_correction_audit_v1',
            'INSERT'
        )::int,
        has_table_privilege(
            'finam',
            'analytics.feature_store_watermark_v1',
            'SELECT'
        )::int,
        has_table_privilege(
            'finam',
            'analytics.feature_store_watermark_v1',
            'UPDATE'
        )::int;
    "
)"

ALEX_STATE="$(
    sudo -u postgres \
    psql -X -d "$DB_NAME" -AtF '|' -c "
    SELECT
        has_schema_privilege(
            'alex',
            'analytics',
            'USAGE'
        )::int,
        has_table_privilege(
            'alex',
            'analytics.feature_store_historical_correction_audit_v1',
            'SELECT'
        )::int,
        has_table_privilege(
            'alex',
            'analytics.feature_store_historical_correction_audit_v1',
            'INSERT'
        )::int,
        has_table_privilege(
            'alex',
            'analytics.feature_store_watermark_v1',
            'SELECT'
        )::int,
        has_table_privilege(
            'alex',
            'analytics.feature_store_watermark_v1',
            'UPDATE'
        )::int;
    "
)"

PUBLIC_STATE="$(
    sudo -u postgres \
    psql -X -d "$DB_NAME" -AtF '|' -c "
    SELECT
        has_table_privilege(
            'public',
            'analytics.feature_store_historical_correction_audit_v1',
            'SELECT'
        )::int,
        has_table_privilege(
            'public',
            'analytics.feature_store_historical_correction_audit_v1',
            'INSERT'
        )::int,
        has_table_privilege(
            'public',
            'analytics.feature_store_watermark_v1',
            'SELECT'
        )::int,
        has_table_privilege(
            'public',
            'analytics.feature_store_watermark_v1',
            'UPDATE'
        )::int;
    "
)"

OWNER_STATE="$(
    sudo -u postgres     psql -X -d "$DB_NAME" -AtF '|' -c "
    SELECT string_agg(
        c.relname || '=' || pg_get_userbyid(c.relowner),
        ',' ORDER BY c.relname
    )
    FROM pg_class c
    JOIN pg_namespace n
      ON n.oid = c.relnamespace
    WHERE n.nspname='analytics'
      AND c.relname IN (
          'feature_store_historical_correction_audit_v1',
          'feature_store_watermark_v1'
      );
    "
)"

echo "finam_state=$FINAM_STATE"
echo "alex_state=$ALEX_STATE"
echo "public_state=$PUBLIC_STATE"
echo "owner_state=$OWNER_STATE"

[[ "$OWNER_STATE" == "feature_store_historical_correction_audit_v1=postgres,feature_store_watermark_v1=postgres" ]] || {
    echo "ERROR=ownership_boundary_invalid:$OWNER_STATE"
    exit 1
}

[[ "$FINAM_STATE" == "1|1|1|1|1" ]] || {
    echo "ERROR=finam_grants_invalid:$FINAM_STATE"
    exit 1
}

[[ "$ALEX_STATE" == "1|1|0|1|0" ]] || {
    echo "ERROR=alex_grants_invalid:$ALEX_STATE"
    exit 1
}

[[ "$PUBLIC_STATE" == "0|0|0|0" ]] || {
    echo "ERROR=public_grants_invalid:$PUBLIC_STATE"
    exit 1
}

DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@127.0.0.1:5432/finam_core}" \
FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE=0.00005 \
PYTHONPATH=src \
python src/scripts/build_feature_store_historical_correction_audit_v1.py \
    --window-bars 20 \
    --symbol BTCUSD \
    --timeframe M1 \
    --dry-run |
    tee /tmp/feature_store_historical_correction_grants_v1.log

grep -q \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1_READY" \
  /tmp/feature_store_historical_correction_grants_v1.log

echo "finam_runtime_access=OK"
echo "alex_read_only_access=OK"
echo "public_access=REVOKED"
echo \
  "VERDICT=TEST_FEATURE_STORE_HISTORICAL_CORRECTION_GRANTS_V1_OK"
