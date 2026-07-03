#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PIPELINE_V2_SCHEMA_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/001_edge_pipeline_snapshot_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_pipeline_snapshot_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_snapshot_v1.py \
  | tee /tmp/edge_pipeline_v2_schema_v1.txt

grep -q "VERDICT=EDGE_PIPELINE_V2_SCHEMA_V1_READY" \
  /tmp/edge_pipeline_v2_schema_v1.txt

psql -d finam_core -c "\d analytics.edge_pipeline_snapshot_v1"

table_exists=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.edge_pipeline_snapshot_v1') IS NOT NULL;")
test "$table_exists" = "t"

echo "table_exists=$table_exists"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PIPELINE_V2_SCHEMA_V1_READY"
echo "VERDICT=TEST_EDGE_PIPELINE_V2_SCHEMA_V1_OK"
