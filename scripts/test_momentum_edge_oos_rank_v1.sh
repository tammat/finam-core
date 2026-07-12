#!/usr/bin/env bash
set -euo pipefail

PYTHONPYCACHEPREFIX=/tmp/momentum_edge_oos_rank_pycache PYTHONPATH=src \
  .venv/bin/python -m py_compile src/scripts/build_momentum_edge_oos_rank_v1.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python src/scripts/build_momentum_edge_oos_rank_v1.py \
  | tee /tmp/momentum_edge_oos_rank_v1.log

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_oos_result_v1 WHERE research_batch_id='20260712_MOMENTUM_THRESHOLD_RECALC_V2' AND validation_version='MOMENTUM_CHRONOLOGICAL_OOS_V1';")
promoted=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_oos_result_v1 WHERE research_batch_id='20260712_MOMENTUM_THRESHOLD_RECALC_V2' AND promotion_allowed;")
unsafe=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_candidate_v1 WHERE micro_live_allowed OR live_allowed;")
test "$rows" = "5"
test "$promoted" = "0"
test "$unsafe" = "0"
grep -q '^VERDICT=MOMENTUM_EDGE_OOS_RANK_V1_READY$' /tmp/momentum_edge_oos_rank_v1.log

echo "oos_registry_rows=$rows"
echo "promotion_allowed_rows=$promoted"
echo "unsafe_live_rows=$unsafe"
echo "VERDICT=TEST_MOMENTUM_EDGE_OOS_RANK_V1_OK"
