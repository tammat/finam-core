#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-/opt/finam-core/runtime/audits}"
LOG_FILE="${LOG_DIR}/hot_query_source_v1.log"

mkdir -p "$LOG_DIR"
exec > >(tee "$LOG_FILE") 2>&1

echo "=== HOT QUERY SOURCE AUDIT V1 ==="
echo "timestamp=$(date -Is)"

show_file_range() {
    local file="$1"
    local from="$2"
    local to="$3"

    echo
    echo "=== FILE $file LINES $from-$to ==="

    if [[ ! -f "$file" ]]; then
        echo "STATUS=file_missing"
        return 0
    fi

    nl -ba "$file" | sed -n "${from},${to}p"
}

show_file_range \
    src/scripts/build_microstructure_health_v1.py \
    1 130

show_file_range \
    src/scripts/run_moex_index_online_v2.py \
    1 130

show_file_range \
    src/scripts/build_edge_pipeline_snapshot_v1.py \
    70 140

show_file_range \
    src/scripts/build_market_snapshot_history_backfill_v1.py \
    1 110

show_file_range \
    src/scripts/build_feature_snapshot_history_backfill_v1.py \
    1 125

show_file_range \
    src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py \
    240 370

show_file_range \
    src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py \
    380 440

echo
echo "=== EXACT MAX COUNT QUERY OWNERS ==="

grep -RIn \
    --include='*.py' \
    --include='*.sql' \
    --include='*.sh' \
    -E \
    'SELECT[[:space:]]+max\(ts\).*count\(\*\)|count\(\*\).*max\(ts\)' \
    src scripts 2>/dev/null || true

echo
echo "=== MICROSTRUCTURE WINDOW QUERY OWNERS ==="

grep -RIn \
    --include='*.py' \
    --include='*.sql' \
    --include='*.sh' \
    -E \
    'lag\(observed_at\)|observed_at.*interval|market_microstructure_snapshot_v1' \
    src scripts 2>/dev/null |
    head -300 || true

echo
echo "=== MARKET SNAPSHOT LATEST QUERY OWNERS ==="

grep -RIn \
    --include='*.py' \
    --include='*.sql' \
    --include='*.sh' \
    -E \
    'ORDER BY .*bar_ts DESC( NULLS LAST)?|market_snapshot_v1.*LIMIT' \
    src scripts 2>/dev/null |
    head -250 || true

echo
echo "=== RUNTIME CALLERS ==="

grep -RIn \
    --include='*.py' \
    --include='*.service' \
    --include='*.timer' \
    --include='*.sh' \
    -E \
    'build_microstructure_health_v1|run_moex_index_online_v2|build_market_snapshot_history_backfill_v1|build_feature_snapshot_history_backfill_v1' \
    src scripts deploy 2>/dev/null |
    head -300 || true

echo
echo "=== SYSTEMD SCHEDULES ==="

systemctl list-timers --all --no-pager |
    grep -Ei \
    'microstructure|market|feature|research|edge|finam' || true

echo
echo "=== PROCESS SNAPSHOT ==="

ps -eo pid,ppid,%cpu,%mem,etime,stat,cmd \
    --sort=-%cpu |
    grep -E \
    'build_microstructure_health_v1|run_moex_index_online_v2|build_market_snapshot_history_backfill_v1|build_feature_snapshot_history_backfill_v1|postgres' |
    grep -v grep |
    head -80 || true

echo
echo "VERDICT=HOT_QUERY_SOURCE_AUDIT_COMPLETE"
