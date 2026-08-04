#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
PG_CLUSTER="${PG_CLUSTER:-17-main}"
CONF="/etc/postgresql/17/main/postgresql.conf"
BACKUP="${CONF}.before_pg_stat_statements_$(date +%Y%m%d_%H%M%S)"

echo "=== ENABLE PG_STAT_STATEMENTS V1 ==="
echo "database=$DB_NAME"
echo "cluster=$PG_CLUSTER"
echo "config=$CONF"

if [[ ! -f "$CONF" ]]; then
    echo "ERROR=postgresql_config_not_found"
    exit 1
fi

echo
echo "=== PRECHECK ==="

sudo -u postgres psql -X -d "$DB_NAME" -Atqc \
    "SELECT current_database(), current_setting('server_version');"

CURRENT_PRELOAD="$(
    sudo -u postgres psql -X -d "$DB_NAME" -Atqc \
        "SHOW shared_preload_libraries;"
)"

echo "current_shared_preload_libraries=$CURRENT_PRELOAD"

sudo cp --preserve=all "$CONF" "$BACKUP"
echo "backup=$BACKUP"

if [[ ",${CURRENT_PRELOAD}," == *",pg_stat_statements,"* ]]; then
    echo "config_change=not_required"
else
    if [[ -z "$CURRENT_PRELOAD" ]]; then
        NEW_PRELOAD="pg_stat_statements"
    else
        NEW_PRELOAD="${CURRENT_PRELOAD},pg_stat_statements"
    fi

    sudo -u postgres psql -X -d "$DB_NAME" -v ON_ERROR_STOP=1 -c \
        "ALTER SYSTEM SET shared_preload_libraries = '${NEW_PRELOAD}';"

    echo "config_change=applied"
    echo "new_shared_preload_libraries=$NEW_PRELOAD"
fi

echo
echo "=== CONFIG VALIDATION ==="

sudo -u postgres \
    /usr/lib/postgresql/17/bin/postgres \
    -D /var/lib/postgresql/17/main \
    -C shared_preload_libraries \
    -c config_file="$CONF"

echo
echo "=== RESTART POSTGRESQL ==="

sudo systemctl restart "postgresql@${PG_CLUSTER}.service"

if ! sudo systemctl is-active --quiet \
    "postgresql@${PG_CLUSTER}.service"; then
    echo "ERROR=postgresql_restart_failed"
    echo "rollback_config=$BACKUP"
    sudo systemctl --no-pager --full status \
        "postgresql@${PG_CLUSTER}.service" || true
    exit 1
fi

echo "postgresql_status=active"

echo
echo "=== CREATE EXTENSION ==="

sudo -u postgres psql \
    -X \
    -d "$DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

echo
echo "=== VERIFY ==="

sudo -u postgres psql -X -d "$DB_NAME" -P pager=off -c "
SELECT
    current_setting('shared_preload_libraries')
        AS shared_preload_libraries,
    current_setting('compute_query_id')
        AS compute_query_id;
"

sudo -u postgres psql -X -d "$DB_NAME" -P pager=off -c "
SELECT
    extname,
    extversion
FROM pg_extension
WHERE extname = 'pg_stat_statements';
"

sudo -u postgres psql -X -d "$DB_NAME" -P pager=off -c "
SELECT
    count(*) AS tracked_statements
FROM pg_stat_statements;
"

echo
echo "VERDICT=PG_STAT_STATEMENTS_ENABLED"
