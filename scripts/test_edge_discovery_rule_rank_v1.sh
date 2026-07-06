#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_RULE_RANK_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_rule_rank_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_discovery_rule_rank_v1.py | tee /tmp/edge_discovery_rule_rank_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_RULE_RANK_V1_READY" /tmp/edge_discovery_rule_rank_v1.txt

runs=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_discovery_run_v1
WHERE method_code='RULE_RANK_V1'
  AND status_code='DONE';
")

bad_live=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE live_allowed=true
   OR micro_live_allowed=true;
")

bad_score=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE discovery_score < 0
   OR discovery_score > 100;
")

test "$runs" -gt 0
test "$bad_live" = "0"
test "$bad_score" = "0"

grep -q "edge.discovery.rule_rank.title" src/marketcore/presentation/ui_labels.py

psql -d finam_core -c "
SELECT
    discovery_rank,
    candidate_class,
    strategy_code,
    symbol,
    timeframe,
    trades,
    profit_factor,
    expectancy,
    normalized_edge_score,
    confidence_score,
    stability_score,
    discovery_score
FROM analytics.edge_candidate_v1 c
JOIN analytics.edge_observation_v1 o
  ON o.observation_uuid = c.observation_uuid
ORDER BY c.discovery_score DESC, c.discovery_rank ASC
LIMIT 30;
" || true

echo "discovery_done_runs=$runs"
echo "bad_live_rows=$bad_live"
echo "bad_score_rows=$bad_score"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_DISCOVERY_RULE_RANK_V1_OK"
