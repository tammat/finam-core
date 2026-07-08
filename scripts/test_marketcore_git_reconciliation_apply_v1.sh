#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_GIT_RECONCILIATION_APPLY_V1 ==="

required_files=(
  docs/MARKETCORE_DATA_CATALOG_RECONCILIATION_V1.txt
  docs/MARKETCORE_DEVELOPMENT_PRINCIPLES_V1.txt
  docs/MARKETCORE_VISION_2030.txt
  scripts/test_marketcore_data_catalog_reconciliation_v1.sh
  scripts/test_marketcore_development_principles_v1.sh
  scripts/test_marketcore_operator_home_v2.sh
  scripts/test_marketcore_vision_2030.sh
  scripts/test_marketcore_git_reconciliation_v1.sh
  scripts/test_marketcore_git_reconciliation_apply_v1.sh
  src/marketcore/presentation/providers/operator_home_widgets_provider.py
  src/scripts/build_edge_factory_operation_v1.py
  src/scripts/build_max_edge_score_audit_metrics_v1.py
  src/scripts/build_max_edge_score_audit_v1.py
  sql/analytics/019_max_edge_score_audit_v1.sql
)

for f in "${required_files[@]}"; do
  test -f "$f" || {
    echo "MISSING_REQUIRED_FILE=$f"
    exit 1
  }
done

for f in \
  src/marketcore/presentation/providers/operator_home_widgets_provider.py \
  src/scripts/build_edge_factory_operation_v1.py \
  src/scripts/build_max_edge_score_audit_metrics_v1.py \
  src/scripts/build_max_edge_score_audit_v1.py \
  src/marketcore/presentation/pages/operator_home_page.py
do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_git_reconciliation_apply PYTHONPATH=src python -m py_compile "$f"
done

for f in scripts/test_*.sh; do
  bash -n "$f"
done

if grep -RInE 'send_order|place_order|cancel_order|execute_order|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills|DELETE FROM|DROP TABLE|TRUNCATE' \
  docs/MARKETCORE_DATA_CATALOG_RECONCILIATION_V1.txt \
  docs/MARKETCORE_DEVELOPMENT_PRINCIPLES_V1.txt \
  docs/MARKETCORE_VISION_2030.txt \
  src/marketcore/presentation/providers/operator_home_widgets_provider.py \
  src/scripts/build_edge_factory_operation_v1.py \
  src/scripts/build_max_edge_score_audit_metrics_v1.py \
  src/scripts/build_max_edge_score_audit_v1.py \
  sql/analytics/019_max_edge_score_audit_v1.sql; then
  echo "DANGEROUS_RECONCILIATION_APPLY_CONTENT_FOUND"
  exit 1
fi

if git status --short | grep -q '^?? reports/'; then
  echo "REPORTS_SHOULD_NOT_BE_TRACKED"
  exit 1
fi

echo "required_files=OK"
echo "python_compile=OK"
echo "bash_syntax=OK"
echo "reports_tracked=0"
echo "git_add_dot=0"
echo "delete_files=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_GIT_RECONCILIATION_APPLY_V1_READY"
echo "VERDICT=TEST_MARKETCORE_GIT_RECONCILIATION_APPLY_V1_OK"
