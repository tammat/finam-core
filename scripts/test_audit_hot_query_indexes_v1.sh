#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
DB_USER="${DB_USER:-alex}"
SCRIPT="/opt/finam-core/scripts/audit_hot_query_indexes_v1.sh"
LOG="/opt/finam-core/runtime/audits/hot_query_indexes_v1.log"

echo "=== TEST_HOT_QUERY_INDEX_AUDIT_V1 ==="

[[ -x "$SCRIPT" ]] || {
    echo "ERROR=audit_script_not_executable"
    exit 1
}

DB_NAME="$DB_NAME" \
DB_USER="$DB_USER" \
"$SCRIPT" >/dev/null

[[ -s "$LOG" ]] || {
    echo "ERROR=audit_log_missing"
    exit 1
}

if grep -qiE 'ОШИБКА:|ERROR:.*syntax|syntax error' "$LOG"; then
    echo "ERROR=sql_or_script_error_present_in_log"
    grep -iE 'ОШИБКА:|ERROR:.*syntax|syntax error' "$LOG" || true
    exit 1
fi

for section in \
    "=== EXISTING INDEXES ===" \
    "=== INDEX USAGE ===" \
    "=== EXPLAIN MICROSTRUCTURE RECENT ===" \
    "=== EXPLAIN MARKET SNAPSHOT LATEST ===" \
    "=== EXPLAIN MARKET BARS MAX ===" \
    "=== SQL OWNERS IN SOURCE ==="
do
    grep -qF "$section" "$LOG" || {
        echo "ERROR=missing_section:${section}"
        exit 1
    }
done

grep -q \
    "VERDICT=HOT_QUERY_INDEX_AUDIT_COMPLETE" \
    "$LOG" || {
        echo "ERROR=success_verdict_missing"
        exit 1
    }

echo "database=$DB_NAME"
echo "log_file=$LOG"
echo "VERDICT=TEST_HOT_QUERY_INDEX_AUDIT_V1_OK"
exit 0
