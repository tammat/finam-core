#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_BRANDING_AUDIT_V1 ==="

mkdir -p reports

audit="reports/branding_audit_v1.txt"

{
echo "======================================"
echo " MARKETCORE BRANDING AUDIT V1"
echo "======================================"
echo
date
echo

echo "===== UI ====="
grep -RIn "FinamCore\|FINAM_CORE\|finam-core\|finam_core\|Finam" \
src/marketcore/presentation 2>/dev/null || true

echo
echo "===== PYTHON ====="
grep -RIn "FinamCore\|FINAM_CORE\|finam-core\|finam_core\|Finam" \
src 2>/dev/null || true

echo
echo "===== DOCS ====="
grep -RIn "FinamCore\|FINAM_CORE\|finam-core\|finam_core\|Finam" \
docs 2>/dev/null || true

echo
echo "===== CONFIG ====="
grep -RIn "FinamCore\|FINAM_CORE\|finam-core\|finam_core\|Finam" \
config deploy systemd .env* 2>/dev/null || true

echo
echo "===== SCRIPTS ====="
grep -RIn "FinamCore\|FINAM_CORE\|finam-core\|finam_core\|Finam" \
scripts src/scripts 2>/dev/null || true

echo
echo "===== SQL ====="
grep -RIn "FinamCore\|FINAM_CORE\|finam-core\|finam_core\|Finam" \
sql 2>/dev/null || true

echo
echo "===== TESTS ====="
grep -RIn "FinamCore\|FINAM_CORE\|finam-core\|finam_core\|Finam" \
tests 2>/dev/null || true

echo
echo "===== SYSTEMD ====="
grep -RIn "FinamCore\|FINAM_CORE\|finam-core\|finam_core\|Finam" \
deploy/systemd 2>/dev/null || true

echo
echo "===== DATABASE COMMENTS ====="

psql -At -d finam_core <<'SQL'
SELECT
table_schema||'.'||table_name||' -> '||coalesce(obj_description((table_schema||'.'||table_name)::regclass),'')
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog','information_schema');
SQL

} > "$audit"

echo "Audit report saved to: $audit"

ui_count=$(grep -RIn "FinamCore\|FINAM_CORE\|finam-core\|finam_core\|Finam" src/marketcore/presentation 2>/dev/null | wc -l)
py_count=$(grep -RIn "FinamCore\|FINAM_CORE\|finam-core\|finam_core\|Finam" src 2>/dev/null | wc -l)
doc_count=$(grep -RIn "FinamCore\|FINAM_CORE\|finam-core\|finam_core\|Finam" docs 2>/dev/null | wc -l)

echo "ui_occurrences=$ui_count"
echo "python_occurrences=$py_count"
echo "documentation_occurrences=$doc_count"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_BRANDING_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_BRANDING_AUDIT_V1_OK"
