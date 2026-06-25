#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_EDGE_SCORECARD_PERSISTENCE_VALIDATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_edge_scorecard_persistence_validation_v1.py

src/scripts/research/build_global_edge_scorecard_persistence_validation_v1.py \
  | tee /tmp/global_edge_scorecard_persistence_validation_v1.out

grep -q "GLOBAL_EDGE_SCORECARD_PERSISTENCE_VALIDATION_V1" /tmp/global_edge_scorecard_persistence_validation_v1.out
grep -q "run_id=" /tmp/global_edge_scorecard_persistence_validation_v1.out
grep -q "run_rows_total=231" /tmp/global_edge_scorecard_persistence_validation_v1.out
grep -q "run_positive_rows=65" /tmp/global_edge_scorecard_persistence_validation_v1.out
grep -q "run_research_candidates=1" /tmp/global_edge_scorecard_persistence_validation_v1.out
grep -q "run_micro_live_candidates=0" /tmp/global_edge_scorecard_persistence_validation_v1.out
grep -q "rows_inserted=231" /tmp/global_edge_scorecard_persistence_validation_v1.out
grep -q "candidate_rows=1" /tmp/global_edge_scorecard_persistence_validation_v1.out
grep -q "VERDICT=GLOBAL_EDGE_SCORECARD_PERSISTENCE_VALIDATION_OK" /tmp/global_edge_scorecard_persistence_validation_v1.out

echo "TEST_GLOBAL_EDGE_SCORECARD_PERSISTENCE_VALIDATION_V1_OK"
