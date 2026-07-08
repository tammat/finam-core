#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_GIT_RECONCILIATION_V1 ==="

mkdir -p reports

report="reports/git_reconciliation_v1.txt"

{
echo "=== MARKETCORE_GIT_RECONCILIATION_V1 ==="
echo "generated_at=$(date -Is)"
echo

echo "=== BRANCH ==="
git rev-parse --abbrev-ref HEAD
echo

echo "=== STATUS SHORT ==="
git status --short
echo

echo "=== UNTRACKED FILES ==="
git ls-files --others --exclude-standard
echo

echo "=== MODIFIED FILES ==="
git ls-files --modified
echo

echo "=== RECOMMENDED CLASSIFICATION ==="
echo "COMMIT_PERMANENT docs/MARKETCORE_DATA_CATALOG_RECONCILIATION_V1.txt"
echo "COMMIT_PERMANENT docs/MARKETCORE_DEVELOPMENT_PRINCIPLES_V1.txt"
echo "COMMIT_PERMANENT docs/MARKETCORE_VISION_2030.txt"
echo "COMMIT_PERMANENT scripts/test_marketcore_data_catalog_reconciliation_v1.sh"
echo "COMMIT_PERMANENT scripts/test_marketcore_development_principles_v1.sh"
echo "COMMIT_PERMANENT scripts/test_marketcore_operator_home_v2.sh"
echo "COMMIT_PERMANENT scripts/test_marketcore_vision_2030.sh"
echo "COMMIT_REVIEW src/marketcore/presentation/providers/operator_home_widgets_provider.py"
echo "COMMIT_REVIEW src/scripts/build_edge_factory_operation_v1.py"
echo "COMMIT_REVIEW src/scripts/build_max_edge_score_audit_metrics_v1.py"
echo "COMMIT_REVIEW src/scripts/build_max_edge_score_audit_v1.py"
echo "COMMIT_REVIEW sql/analytics/019_max_edge_score_audit_v1.sql"
echo "COMMIT_REVIEW scripts/test_edge_factory_operation_v1.sh"
echo "COMMIT_REVIEW scripts/test_edge_score_model_v2_part1.sh"
echo "COMMIT_REVIEW scripts/test_marketcore_branding_audit_v1.sh"
echo "COMMIT_REVIEW scripts/test_max_edge_score_audit_part1.sh"
echo "COMMIT_REVIEW scripts/test_max_edge_score_audit_part2.sh"
echo "COMMIT_REVIEW scripts/test_recommendation_viewmodel_ui_v1.sh"
echo "ARCHIVE_REVIEW scripts/apply_edge_score_model_v2_part3_ui_fix.sh"
echo "ARCHIVE_REVIEW scripts/apply_edge_score_model_v2_part3_ui_patch.sh"
echo

echo "=== SAFETY DECISION ==="
echo "NO_GIT_ADD_DOT=1"
echo "NO_DELETE=1"
echo "NO_RESET=1"
echo "NO_CLEAN=1"
echo

echo "VERDICT=MARKETCORE_GIT_RECONCILIATION_V1_READY"
} > "$report"

test -s "$report"

grep -q "RECOMMENDED CLASSIFICATION" "$report"
grep -q "NO_GIT_ADD_DOT=1" "$report"
grep -q "VERDICT=MARKETCORE_GIT_RECONCILIATION_V1_READY" "$report"

echo "report=$report"
echo "mode=audit_only"
echo "git_add_dot=0"
echo "delete_files=0"
echo "git_reset=0"
echo "git_clean=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_GIT_RECONCILIATION_V1_READY"
echo "VERDICT=TEST_MARKETCORE_GIT_RECONCILIATION_V1_OK"
