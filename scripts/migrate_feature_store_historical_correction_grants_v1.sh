#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
SQL_FILE="$ROOT/sql/analytics/015_feature_store_historical_correction_grants_v1.sql"

DB_NAME="${DB_NAME:-finam_core}"

cd "$ROOT" || exit 1

echo "=== MIGRATE_FEATURE_STORE_HISTORICAL_CORRECTION_GRANTS_V1 ==="

[[ -f "$SQL_FILE" ]] || {
    echo "ERROR=grant_migration_missing"
    exit 1
}

sudo -u postgres \
  psql \
  -X \
  -v ON_ERROR_STOP=1 \
  -d "$DB_NAME" \
  -f "$SQL_FILE"

echo "database=$DB_NAME"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_GRANTS_V1_READY"
