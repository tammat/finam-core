#!/usr/bin/env bash
set -euo pipefail

SCRIPT="/opt/finam-core/scripts/audit_hot_query_source_v1.sh"
LOG="/opt/finam-core/runtime/audits/hot_query_source_v1.log"

echo "=== TEST_HOT_QUERY_SOURCE_AUDIT_V1 ==="

[[ -x "$SCRIPT" ]] || {
    echo "ERROR=audit_script_not_executable"
    exit 1
}

"$SCRIPT" >/dev/null

[[ -s "$LOG" ]] || {
    echo "ERROR=audit_log_missing"
    exit 1
}

for section in \
    "=== EXACT MAX COUNT QUERY OWNERS ===" \
    "=== MICROSTRUCTURE WINDOW QUERY OWNERS ===" \
    "=== MARKET SNAPSHOT LATEST QUERY OWNERS ===" \
    "=== RUNTIME CALLERS ===" \
    "=== SYSTEMD SCHEDULES ==="
do
    grep -qF "$section" "$LOG" || {
        echo "ERROR=missing_section:$section"
        exit 1
    }
done

grep -q \
    "VERDICT=HOT_QUERY_SOURCE_AUDIT_COMPLETE" \
    "$LOG" || {
        echo "ERROR=success_verdict_missing"
        exit 1
    }

echo "log_file=$LOG"
echo "VERDICT=TEST_HOT_QUERY_SOURCE_AUDIT_V1_OK"
