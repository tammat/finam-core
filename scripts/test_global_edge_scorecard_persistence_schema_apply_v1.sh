#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_APPLY_V1 ==="

python3 -m py_compile \
  src/scripts/research/apply_global_edge_scorecard_persistence_schema_v1.py

src/scripts/research/apply_global_edge_scorecard_persistence_schema_v1.py --apply \
  | tee /tmp/global_edge_scorecard_persistence_schema_apply_v1.out

grep -q "GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_APPLY_V1" /tmp/global_edge_scorecard_persistence_schema_apply_v1.out
grep -q "db_update=1" /tmp/global_edge_scorecard_persistence_schema_apply_v1.out
grep -q "tables_applied=2" /tmp/global_edge_scorecard_persistence_schema_apply_v1.out
grep -q "indexes_applied=4" /tmp/global_edge_scorecard_persistence_schema_apply_v1.out
grep -q "VERDICT=GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_APPLY_OK" /tmp/global_edge_scorecard_persistence_schema_apply_v1.out

echo "TEST_GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_APPLY_V1_OK"
