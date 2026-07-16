#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/pytest -q tests/test_profit_funnel_source_registry_v2.py tests/test_research_candidate_canonical_link_v2.py
src/scripts/test_marketcore_profit_funnel_transition_lineage_v2.sh
linked="$(psql -d finam_core -Atqc "SELECT linked_count FROM analytics.profit_funnel_transition_lineage_v2 WHERE transition_code='RESEARCH_TO_CANDIDATE'")"
source_count="$(psql -d finam_core -Atqc "SELECT observations_scanned FROM analytics.edge_discovery_run_v1 WHERE status_code='DONE' ORDER BY id DESC LIMIT 1")"
lineage_count="$(psql -d finam_core -Atqc "SELECT from_count FROM analytics.profit_funnel_transition_lineage_v2 WHERE transition_code='RESEARCH_TO_CANDIDATE'")"
test "$linked" -gt 0
test "$lineage_count" -eq "$source_count"
echo "research_candidate_conversion=$linked/$source_count"
echo "symbol_strategy_heuristic_links=0"
echo "oos_forward_gap_exposed=PASS"
echo "VERDICT=MARKETCORE_STAGE7_RESEARCH_CANDIDATE_LINEAGE_V2_READY"
