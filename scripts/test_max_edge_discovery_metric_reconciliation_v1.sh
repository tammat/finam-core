#!/usr/bin/env bash
set -euo pipefail

PYTHONPYCACHEPREFIX=/tmp/max_edge_metric_reconciliation_pycache PYTHONPATH=src \
  .venv/bin/python -m py_compile src/scripts/build_max_edge_discovery_engine_v1.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python src/scripts/build_max_edge_discovery_engine_v1.py \
  >/tmp/max_edge_metric_reconciliation_v1.log

rows=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.max_edge_ranking_v1
WHERE source_version='MAX_EDGE_DISCOVERY_ENGINE_V1';")
with_economics=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.max_edge_ranking_v1
WHERE source_version='MAX_EDGE_DISCOVERY_ENGINE_V1'
  AND expectancy > 0 AND profit_factor > 1;")
mismatches=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.max_edge_ranking_v1 r
JOIN analytics.edge_candidate_v1 c ON c.id::text=r.candidate_id
JOIN analytics.edge_observation_v1 o ON o.observation_uuid=c.observation_uuid
WHERE r.source_version='MAX_EDGE_DISCOVERY_ENGINE_V1'
  AND (
    abs(r.expectancy-o.expectancy) > 0.000001
    OR abs(r.profit_factor-o.profit_factor) > 0.000001
  );")
distinct_scores=$(psql -At -d finam_core -c "
SELECT count(DISTINCT edge_score) FROM analytics.max_edge_ranking_v1
WHERE source_version='MAX_EDGE_DISCOVERY_ENGINE_V1';")
unsafe=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.edge_candidate_v1
WHERE micro_live_allowed OR live_allowed;")

test "$rows" -gt 0
test "$with_economics" = "$rows"
test "$mismatches" = "0"
test "$distinct_scores" -ge 3
test "$unsafe" = "0"

echo "rows=$rows"
echo "with_economics=$with_economics"
echo "mismatches=$mismatches"
echo "distinct_scores=$distinct_scores"
echo "unsafe_live_rows=$unsafe"
echo "VERDICT=TEST_MAX_EDGE_DISCOVERY_METRIC_RECONCILIATION_V1_OK"
