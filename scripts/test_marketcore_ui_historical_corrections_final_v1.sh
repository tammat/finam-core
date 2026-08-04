#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST MARKETCORE UI HISTORICAL CORRECTIONS FINAL V1 ==="

scripts/test_control_v3_historical_corrections_full_section_v1.sh
scripts/test_control_v3_duplicate_attachments_v2.sh
scripts/test_control_v3_historical_corrections_section_tree_v1.sh
scripts/test_control_v3_historical_corrections_metric_type_v1.sh
scripts/test_control_v3_loader_endpoint_call_validation_v5.sh
scripts/audit_marketcore_ui_historical_corrections_recent_audits_shape_v1.sh
scripts/test_marketcore_ui_historical_corrections_render_tree_v2.sh

echo "writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKETCORE_UI_HISTORICAL_CORRECTIONS_FINAL_V1_OK"
