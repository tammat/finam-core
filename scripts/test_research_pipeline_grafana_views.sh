#!/usr/bin/env bash
set -euo pipefail

test -f scripts/create_research_pipeline_grafana_views.sql

grep -q "v_research_pipeline_runs_grafana" scripts/create_research_pipeline_grafana_views.sql
grep -q "v_research_pipeline_steps_grafana" scripts/create_research_pipeline_grafana_views.sql
grep -q "v_strategy_lifecycle_grafana" scripts/create_research_pipeline_grafana_views.sql
grep -q "v_strategy_promotion_decisions_grafana" scripts/create_research_pipeline_grafana_views.sql
grep -q "v_trade_fill_quality_audit_grafana" scripts/create_research_pipeline_grafana_views.sql

echo "TEST_RESEARCH_PIPELINE_GRAFANA_VIEWS_OK"
