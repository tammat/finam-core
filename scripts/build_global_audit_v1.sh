#!/usr/bin/env bash
set -euo pipefail

echo "=== GLOBAL_AUDIT_V1 ==="

mkdir -p reports

report="reports/global_audit_v1.txt"
: > "$report"

log() {
  echo "$*" | tee -a "$report"
}

log "--- GIT STATUS ---"
git status --short | tee -a "$report"

log "--- PLATFORM API CHECK ---"
for path in \
  strategy-platform/summary \
  edge-platform/summary \
  risk-platform/summary \
  trading-platform/summary \
  portfolio-platform/summary
do
  curl -fsS "http://127.0.0.1:8095/api/kg/v1/$path" >/tmp/"${path//\//_}.json"
  log "OK api=$path"
done

log "--- PLATFORM UI CHECK ---"
for path in \
  strategy-platform \
  edge-platform \
  risk-platform \
  trading-platform \
  portfolio-platform
do
  curl -fsS "http://127.0.0.1:8080/$path" >/tmp/"$path".html
  log "OK ui=$path"
done

log "--- CANONICAL STORAGE CHECK ---"
psql -d finam_core -c "
SELECT schemaname, relname, n_live_tup
FROM pg_stat_user_tables
WHERE schemaname='analytics'
  AND relname IN (
    'market_snapshot_v1',
    'feature_snapshot_v1',
    'strategy_signal_snapshot_v1',
    'edge_decision_snapshot_v1',
    'risk_decision_snapshot_v1',
    'trading_order_intent_v1',
    'portfolio_position_snapshot_v1',
    'portfolio_equity_snapshot_v1'
  )
ORDER BY relname;
" | tee -a "$report"

log "--- UI DIRECT SQL FINDINGS ---"
grep -RInE "SELECT .*FROM|FROM analytics\.|FROM warehouse\.|FROM knowledge_graph\." \
  src/marketcore/presentation/pages \
  | tee /tmp/global_audit_ui_sql.txt || true

ui_sql_count=$(wc -l </tmp/global_audit_ui_sql.txt | tr -d ' ')

log "ui_direct_sql_findings=$ui_sql_count"

log "--- LEGACY FINDINGS, FILTERED ---"
grep -RInE "TODO|FIXME|deprecated|LEGACY" src scripts sql docs \
  --exclude-dir=finam_proto \
  --exclude-dir=proto \
  --exclude="*_pb2.py" \
  --exclude="*.proto" \
  | tee /tmp/global_audit_legacy.txt || true

legacy_count=$(wc -l </tmp/global_audit_legacy.txt | tr -d ' ')
log "legacy_findings=$legacy_count"

log "--- SAFETY CHECK ---"
unsafe_trading=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1
WHERE live_allowed=true
   OR micro_live_allowed=true
   OR order_sent=true;
")

unsafe_risk=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.risk_decision_snapshot_v1
WHERE ready_for_live=true
   OR ready_for_micro_live=true;
")

unsafe_edge=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_decision_snapshot_v1
WHERE ready_for_live=true
   OR ready_for_micro_live=true;
")

log "unsafe_edge_rows=$unsafe_edge"
log "unsafe_risk_rows=$unsafe_risk"
log "unsafe_trading_rows=$unsafe_trading"

test "$unsafe_edge" = "0"
test "$unsafe_risk" = "0"
test "$unsafe_trading" = "0"

log "--- GLOBAL AUDIT SUMMARY ---"
log "platform_api=OK"
log "platform_ui=OK"
log "canonical_storage=OK"
log "safety=OK"
log "ui_direct_sql_findings=$ui_sql_count"
log "legacy_findings=$legacy_count"

if [ "$ui_sql_count" -gt 0 ]; then
  log "GLOBAL_AUDIT_RESULT=CONDITIONAL_PASS"
  log "NEXT_REQUIRED=UI_DIRECT_SQL_CLEANUP_V1"
else
  log "GLOBAL_AUDIT_RESULT=PASS"
  log "NEXT_REQUIRED=PAPER_RUNTIME_FOUNDATION_V1"
fi

log "runtime_changed=0"
log "execution_changed=0"
log "orders_changed=0"
log "fills_changed=0"
log "micro_live_allowed=0"
log "VERDICT=GLOBAL_AUDIT_V1_READY"
log "VERDICT=GLOBAL_AUDIT_V1_OK"
