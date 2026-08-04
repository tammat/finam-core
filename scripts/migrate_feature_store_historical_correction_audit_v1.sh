#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
SQL_FILE="$ROOT/sql/analytics/014_feature_store_historical_correction_audit_v1.sql"

DB_NAME="${DB_NAME:-finam_core}"
DB_USER="${DB_USER:-postgres}"

cd "$ROOT" || exit 1

echo "=== MIGRATE_FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1 ==="

[[ -f "$SQL_FILE" ]] || {
    echo "ERROR=migration_file_missing"
    exit 1
}

sudo -u "$DB_USER" \
    psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -d "$DB_NAME" \
    -f "$SQL_FILE"

echo "database=$DB_NAME"
echo "migration_file=$SQL_FILE"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_MIGRATION_V1_READY"
