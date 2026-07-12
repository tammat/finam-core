#!/usr/bin/env bash
set -euo pipefail

batch_id="${RESEARCH_BATCH_ID:-20260712_MOMENTUM_THRESHOLD_RECALC_V2}"

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1 WHERE research_batch_id='$batch_id';")
distinct_results=$(psql -At -d finam_core -c "SELECT count(DISTINCT (trades,profit_factor,expectancy,max_drawdown)) FROM analytics.edge_observation_v1 WHERE research_batch_id='$batch_id';")
scored=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1 WHERE research_batch_id='$batch_id' AND score_formula_version='EDGE_SCORE_FORMULA_V2';")
eligible=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1 WHERE research_batch_id='$batch_id' AND trades>=20 AND profit_factor>=1.05 AND expectancy>0 AND normalized_edge_score>=40 AND confidence_score>=40 AND stability_score>=40;")
unsafe=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_candidate_v1 WHERE micro_live_allowed OR live_allowed;")

test "$rows" = "5"
test "$distinct_results" = "5"
test "$scored" = "5"
test "$eligible" -gt 0
test "$eligible" -lt "$rows"
test "$unsafe" = "0"

echo "rows=$rows"
echo "distinct_results=$distinct_results"
echo "scored=$scored"
echo "trust_gate_eligible=$eligible"
echo "trust_gate_rejected=$((rows-eligible))"
echo "unsafe_live_rows=$unsafe"
echo "VERDICT=TEST_MOMENTUM_EDGE_RECALCULATION_V2_OK"
