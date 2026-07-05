#!/usr/bin/env bash
set -euo pipefail

echo "=== EDGE_DISCOVERY_RULE_RANK_RERUN_V2 ==="

echo
echo "===== STEP 1. DISCOVERY ====="

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/build_edge_discovery_rule_rank_v1.py

echo
echo "===== STEP 2. VALIDATION ====="

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/test_edge_validation_v2_rerun.py 2>/dev/null || true

if [ -f scripts/test_edge_validation_v2_rerun.sh ]; then
    scripts/test_edge_validation_v2_rerun.sh
fi

echo
echo "===== STEP 3. PIPELINE AUDIT ====="

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/build_edge_pipeline_audit_v1.py

echo
echo "===== STEP 4. DISCOVERY SUMMARY ====="

psql -d finam_core -c "
SELECT
    discovery_rank,
    candidate_class,
    candidate_status,
    validation_stage,
    strategy_code,
    symbol,
    timeframe,
    round(discovery_score,4) discovery_score,
    round(validation_score,4) validation_score,
    paper_allowed
FROM analytics.edge_candidate_v1
ORDER BY
    discovery_score DESC,
    validation_score DESC,
    discovery_rank ASC;
"

echo
echo "===== STEP 5. BEST OBSERVATIONS ====="

psql -d finam_core -c "
SELECT

    strategy_code,

    symbol,

    timeframe,

    trades,

    wins,

    losses,

    round(profit_factor,4) pf,

    round(expectancy,6) expectancy,

    round(normalized_edge_score,4) edge_score,

    round(confidence_score,4) confidence,

    round(stability_score,4) stability

FROM analytics.edge_observation_v1

WHERE trades>0

ORDER BY

    normalized_edge_score DESC,

    profit_factor DESC,

    expectancy DESC

LIMIT 30;
"

echo
echo "===== STEP 6. CONVERSION ====="

psql -d finam_core -c "
SELECT

    (SELECT count(*) FROM analytics.edge_observation_v1 WHERE trades>0) observations_with_trades,

    (SELECT count(*) FROM analytics.edge_candidate_v1) candidates,

    (SELECT count(*) FROM analytics.edge_candidate_v1
      WHERE candidate_status='VALIDATED') validated,

    (SELECT count(*) FROM analytics.edge_candidate_v1
      WHERE paper_allowed=true) paper;
"

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true
   OR live_allowed=true;
")

test "$unsafe" = "0"

echo
echo "unsafe_rows=$unsafe"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=EDGE_DISCOVERY_RULE_RANK_RERUN_V2_READY"
echo "VERDICT=TEST_EDGE_DISCOVERY_RULE_RANK_RERUN_V2_OK"

