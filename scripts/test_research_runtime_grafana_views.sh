#!/usr/bin/env bash
set -euo pipefail

test -f scripts/create_research_runtime_grafana_views.sql

grep -q "v_research_runtime_state_grafana" scripts/create_research_runtime_grafana_views.sql
grep -q "v_research_runtime_cycle_log_grafana" scripts/create_research_runtime_grafana_views.sql
grep -q "research_runtime_state" scripts/create_research_runtime_grafana_views.sql
grep -q "research_runtime_cycle_log" scripts/create_research_runtime_grafana_views.sql

echo "TEST_RESEARCH_RUNTIME_GRAFANA_VIEWS_OK"
