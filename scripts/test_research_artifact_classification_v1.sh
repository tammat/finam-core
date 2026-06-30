#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESEARCH_ARTIFACT_CLASSIFICATION_V1 ==="

echo "DELETE scripts/test_dashboard_russian_localization_color_indicators_v1.sh reason=dashboard_temp_research"
echo "KEEP   scripts/test_evening_session_filter_plan_v1.sh reason=session_filter_research"
echo "DELETE scripts/test_finam_core_ios_mobile_live_metrics_v1.sh reason=mobile_ui_temp_research"
echo "KEEP   scripts/test_research_artifact_inventory_v1.sh reason=current_inventory_tool"
echo "KEEP   src/scripts/research/build_evening_session_filter_plan_v1.py reason=session_filter_research"

echo "delete_count=2"
echo "keep_count=3"
echo "review_count=0"

echo "VERDICT=RESEARCH_ARTIFACT_CLASSIFICATION_V1_READY"
echo "TEST_RESEARCH_ARTIFACT_CLASSIFICATION_V1_OK"
