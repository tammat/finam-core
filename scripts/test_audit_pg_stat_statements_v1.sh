#!/usr/bin/env bash
set -uo pipefail

DB_NAME="${DB_NAME:-finam_core}"
DB_USER="${DB_USER:-alex}"
SCRIPT="/opt/finam-core/scripts/audit_pg_stat_statements_v1.sh"
LOG="/opt/finam-core/runtime/audits/pg_stat_statements_audit_v1.log"

echo "=== TEST_PG_STAT_STATEMENTS_AUDIT_V1 ==="

[[ -x "$SCRIPT" ]] || {
    echo "ERROR=audit_script_not_executable"
    exit 1
}

set +e
DB_NAME="$DB_NAME" \
DB_USER="$DB_USER" \
"$SCRIPT" >/dev/null
rc=$?
set -e

[[ -s "$LOG" ]] || {
    echo "ERROR=audit_log_missing"
    exit 1
}

grep -q "=== EXTENSION STATUS ===" "$LOG" || {
    echo "ERROR=extension_status_missing"
    exit 1
}

case "$rc" in
    0)
        grep -q \
            "VERDICT=PG_STAT_STATEMENTS_AUDIT_COMPLETE" \
            "$LOG" || {
                echo "ERROR=success_verdict_missing"
                exit 1
            }
        echo "mode=extension_ready"
        ;;
    2)
        grep -q \
            "VERDICT=PG_STAT_STATEMENTS_AUDIT_PREREQUISITE_MISSING" \
            "$LOG" || {
                echo "ERROR=prerequisite_verdict_missing"
                exit 1
            }
        echo "mode=extension_prerequisite_missing"
        ;;
    *)
        echo "ERROR=unexpected_return_code_$rc"
        exit "$rc"
        ;;
esac

echo "log_file=$LOG"
echo "VERDICT=TEST_PG_STAT_STATEMENTS_AUDIT_V1_OK"
exit 0
