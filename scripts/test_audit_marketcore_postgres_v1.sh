#!/usr/bin/env bash
set -uo pipefail

DB_NAME="${DB_NAME:-finam_core}"
DB_USER="${DB_USER:-alex}"
AUDIT_SCRIPT="/opt/finam-core/scripts/audit_marketcore_postgres_v1.sh"
LOG_FILE="/opt/finam-core/runtime/audits/marketcore_postgres_audit_v1.log"

echo "=== TEST_MARKETCORE_POSTGRES_AUDIT_V1 ==="

if [[ ! -x "$AUDIT_SCRIPT" ]]; then
    echo "ERROR=audit_script_not_executable"
    exit 1
fi

if ! psql -X -U "$DB_USER" -d "$DB_NAME" -Atqc \
    "SELECT current_database();" |
    grep -qx "$DB_NAME"; then
    echo "ERROR=database_connection_failed"
    exit 1
fi

DB_NAME="$DB_NAME" \
DB_USER="$DB_USER" \
"$AUDIT_SCRIPT" >/dev/null

rc=$?

if [[ "$rc" -ne 0 ]]; then
    echo "ERROR=audit_return_code_$rc"
    exit "$rc"
fi

if [[ ! -s "$LOG_FILE" ]]; then
    echo "ERROR=audit_log_missing_or_empty"
    exit 1
fi

grep -q "=== SERVER SETTINGS ===" "$LOG_FILE" || {
    echo "ERROR=settings_section_missing"
    exit 1
}

grep -q "=== ACTIVE QUERIES ===" "$LOG_FILE" || {
    echo "ERROR=active_queries_section_missing"
    exit 1
}

grep -q "=== LARGEST TABLES ===" "$LOG_FILE" || {
    echo "ERROR=largest_tables_section_missing"
    exit 1
}

grep -q "VERDICT=MARKETCORE_POSTGRES_AUDIT_COMPLETE" "$LOG_FILE" || {
    echo "ERROR=success_verdict_missing"
    exit 1
}

echo "database=$DB_NAME"
echo "log_file=$LOG_FILE"
echo "VERDICT=TEST_MARKETCORE_POSTGRES_AUDIT_V1_OK"
exit 0
