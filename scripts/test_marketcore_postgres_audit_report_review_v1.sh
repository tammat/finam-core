#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_POSTGRES_AUDIT_REPORT_REVIEW_V1 ==="

mkdir -p reports

audit="reports/postgres_audit_v1.txt"
plan="reports/postgres_cleanup_plan_v1.txt"
allowlist="reports/postgres_cleanup_allowlist_v1.txt"
review="reports/postgres_audit_report_review_v1.txt"

test -s "$audit"
test -s "$plan"
test -s "$allowlist"

{
echo "=== MARKETCORE POSTGRES AUDIT REPORT REVIEW V1 ==="
echo "generated_at=$(date -Is)"
echo
echo "SOURCE_REPORTS"
echo "- $audit"
echo "- $plan"
echo "- $allowlist"
echo

echo "=== REVIEW SUMMARY ==="
echo "Audit, cleanup plan and allowlist exist."
echo "No destructive maintenance is approved at this stage."
echo "Only VACUUM ANALYZE / ANALYZE may be considered in next apply stage."
echo

echo "=== DATABASE SIZE ==="
grep -A 10 "=== DATABASE SIZE ===" "$audit" || true
echo

echo "=== TOP DEAD TUPLE TABLES ==="
grep -A 60 "=== CANDIDATE DEAD-TUPLE TABLES FOR VACUUM ===" "$plan" || true
echo

echo "=== TABLES WITHOUT ANALYZE ==="
grep -A 60 "=== ANALYZE_ALLOWLIST ===" "$allowlist" || true
echo

echo "=== EMPTY TABLES REVIEW ONLY ==="
grep -A 60 "=== REVIEW_ONLY_EMPTY_TABLES ===" "$allowlist" || true
echo

echo "=== TECHNICAL NAME TABLES REVIEW ONLY ==="
grep -A 80 "=== REVIEW_ONLY_TECHNICAL_NAMES ===" "$allowlist" || true
echo

echo "=== RECOMMENDATION CLASSES ==="
echo "APPLY_NOW:"
echo "- VACUUM ANALYZE tables from VACUUM_ANALYZE_ALLOWLIST only."
echo "- ANALYZE tables from ANALYZE_ALLOWLIST only."
echo
echo "MANUAL_REVIEW:"
echo "- Empty tables."
echo "- tmp/backup/old/test/copy/staging-like tables."
echo
echo "PRESERVE:"
echo "- analytics.edge_score%"
echo "- analytics.%shadow%"
echo "- analytics.%research%"
echo "- analytics.%checkpoint%"
echo "- orders"
echo "- fills"
echo

echo "=== SAFETY DECISION ==="
echo "DELETE_ALLOWED=0"
echo "DROP_ALLOWED=0"
echo "TRUNCATE_ALLOWED=0"
echo "RUNTIME_MUTATION_ALLOWED=0"
echo "EXECUTION_MUTATION_ALLOWED=0"
echo

echo "VERDICT=MARKETCORE_POSTGRES_AUDIT_REPORT_REVIEW_V1_READY"
} > "$review"

test -s "$review"

grep -q "SOURCE_REPORTS" "$review"
grep -q "RECOMMENDATION CLASSES" "$review"
grep -q "APPLY_NOW" "$review"
grep -q "MANUAL_REVIEW" "$review"
grep -q "PRESERVE" "$review"
grep -q "DELETE_ALLOWED=0" "$review"
grep -q "DROP_ALLOWED=0" "$review"
grep -q "TRUNCATE_ALLOWED=0" "$review"
grep -q "VERDICT=MARKETCORE_POSTGRES_AUDIT_REPORT_REVIEW_V1_READY" "$review"

if grep -E '^[[:space:]]*(DELETE[[:space:]]+FROM|DROP[[:space:]]+TABLE|TRUNCATE[[:space:]]+TABLE|UPDATE[[:space:]]+runtime|UPDATE[[:space:]]+execution)' "$review"; then
  echo "DESTRUCTIVE_SQL_FOUND_IN_REVIEW"
  exit 1
fi

echo "review=$review"
echo "review_mode=read_only"
echo "delete_allowed=0"
echo "drop_allowed=0"
echo "truncate_allowed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_POSTGRES_AUDIT_REPORT_REVIEW_V1_READY"
echo "VERDICT=TEST_MARKETCORE_POSTGRES_AUDIT_REPORT_REVIEW_V1_OK"
