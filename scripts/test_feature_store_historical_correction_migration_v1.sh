#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
SQL_FILE="$ROOT/sql/analytics/014_feature_store_historical_correction_audit_v1.sql"
BUILDER="$ROOT/src/scripts/build_feature_store_historical_correction_audit_v1.py"

DB_NAME="${DB_NAME:-finam_core}"

cd "$ROOT" || exit 1

echo "=== TEST_FEATURE_STORE_HISTORICAL_CORRECTION_MIGRATION_V1 ==="

[[ -f "$SQL_FILE" ]] || {
    echo "ERROR=migration_missing"
    exit 1
}

[[ -f "$BUILDER" ]] || {
    echo "ERROR=builder_missing"
    exit 1
}

bash -n \
  scripts/migrate_feature_store_historical_correction_audit_v1.sh

PYTHONPATH=src python -m py_compile "$BUILDER"

python3 - <<'PY'
from pathlib import Path

sql = Path(
    "sql/analytics/"
    "014_feature_store_historical_correction_audit_v1.sql"
).read_text(encoding="utf-8")

builder = Path(
    "src/scripts/"
    "build_feature_store_historical_correction_audit_v1.py"
).read_text(encoding="utf-8")

required_sql = [
    "BEGIN;",
    "CREATE TABLE IF NOT EXISTS",
    "feature_store_historical_correction_audit_v1",
    "audit_run_id uuid NOT NULL",
    "correction_detected boolean NOT NULL",
    "ix_feature_store_historical_correction_audit_run_v1",
    "ix_feature_store_historical_correction_audit_pair_v1",
    "ix_feature_store_historical_correction_detected_v1",
    "COMMIT;",
]

for token in required_sql:
    if token not in sql:
        raise SystemExit(
            f"ERROR=migration_contract_missing:{token}"
        )

for forbidden in (
    "CREATE TABLE IF NOT EXISTS analytics."
    "feature_store_historical_correction_audit_v1",
    "cur.execute(DDL)",
):
    if forbidden in builder:
        raise SystemExit(
            f"ERROR=builder_ddl_remains:{forbidden}"
        )

required_builder = [
    "to_regclass",
    "014_feature_store_historical_correction_audit_v1.sql",
]

for token in required_builder:
    if token not in builder:
        raise SystemExit(
            f"ERROR=builder_migration_guard_missing:{token}"
        )

print("source_contract=OK")
PY

TABLE_EXISTS="$(
    sudo -u postgres     psql -X -d "$DB_NAME" -Atqc "
    SELECT (
        to_regclass(
            'analytics.feature_store_historical_correction_audit_v1'
        ) IS NOT NULL
    )::int;
    "
)"

[[ "$TABLE_EXISTS" == "1" ]] || {
    echo "ERROR=audit_table_missing"
    exit 1
}

COLUMN_COUNT="$(
    sudo -u postgres     psql -X -d "$DB_NAME" -Atqc "
    SELECT count(*)
    FROM information_schema.columns
    WHERE table_schema='analytics'
      AND table_name=
        'feature_store_historical_correction_audit_v1';
    "
)"

[[ "$COLUMN_COUNT" -ge 14 ]] || {
    echo "ERROR=unexpected_column_count:$COLUMN_COUNT"
    exit 1
}

INDEX_COUNT="$(
    sudo -u postgres     psql -X -d "$DB_NAME" -Atqc "
    SELECT count(*)
    FROM pg_indexes
    WHERE schemaname='analytics'
      AND tablename=
        'feature_store_historical_correction_audit_v1';
    "
)"

[[ "$INDEX_COUNT" -ge 4 ]] || {
    echo "ERROR=unexpected_index_count:$INDEX_COUNT"
    exit 1
}

FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE=0.00005 \
PYTHONPATH=src \
python "$BUILDER" \
    --window-bars 20 \
    --symbol BTCUSD \
    --timeframe M1 \
    --dry-run |
    tee /tmp/feature_store_historical_correction_migration_v1.log

grep -q \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1_READY" \
  /tmp/feature_store_historical_correction_migration_v1.log

echo "table_exists=1"
echo "column_count=$COLUMN_COUNT"
echo "index_count=$INDEX_COUNT"
echo "builder_ddl_removed=1"
echo "VERDICT=TEST_FEATURE_STORE_HISTORICAL_CORRECTION_MIGRATION_V1_OK"
