#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
PG_CLUSTER="${PG_CLUSTER:-17-main}"

echo "=== TEST_ENABLE_PG_STAT_STATEMENTS_V1 ==="

systemctl is-active --quiet \
    "postgresql@${PG_CLUSTER}.service" || {
        echo "ERROR=postgresql_not_active"
        exit 1
    }

PRELOADED="$(
    sudo -u postgres psql -X -d "$DB_NAME" -Atqc \
        "SHOW shared_preload_libraries;"
)"

echo "shared_preload_libraries=$PRELOADED"

grep -qw "pg_stat_statements" <<< \
    "${PRELOADED//,/ }" || {
        echo "ERROR=pg_stat_statements_not_preloaded"
        exit 1
    }

INSTALLED="$(
    sudo -u postgres psql -X -d "$DB_NAME" -Atqc "
    SELECT EXISTS (
        SELECT 1
        FROM pg_extension
        WHERE extname = 'pg_stat_statements'
    );
    "
)"

[[ "$INSTALLED" == "t" ]] || {
    echo "ERROR=pg_stat_statements_not_installed"
    exit 1
}

sudo -u postgres psql -X -d "$DB_NAME" -Atqc "
SELECT count(*) >= 0
FROM pg_stat_statements;
" | grep -qx "t" || {
    echo "ERROR=pg_stat_statements_view_unavailable"
    exit 1
}

echo
echo "=== MARKETCORE SERVICES ==="

FAILED=0

for service in \
    finam-paper-safe.service \
    finam-governance.service \
    finam-analytics-supervisor.service \
    finam-research-runtime.service \
    finam-projection-worker.service \
    finam-marketcore-dashboard.service \
    marketcore-kg-api.service
do
    if systemctl is-active --quiet "$service"; then
        echo "SERVICE_OK=$service"
    else
        echo "SERVICE_FAILED=$service"
        FAILED=1
    fi
done

if [[ "$FAILED" -ne 0 ]]; then
    echo "ERROR=marketcore_service_not_active"
    exit 1
fi

echo
echo "VERDICT=TEST_ENABLE_PG_STAT_STATEMENTS_V1_OK"
