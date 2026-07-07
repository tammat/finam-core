#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_PART2 ==="

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_score_model_v2_reconciliation.py

out=$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python src/scripts/build_edge_score_model_v2_reconciliation.py)
echo "$out"

echo "$out" | grep -q "runtime_changed=0"
echo "$out" | grep -q "execution_changed=0"
echo "$out" | grep -q "orders_changed=0"
echo "$out" | grep -q "fills_changed=0"
echo "$out" | grep -q "micro_live_allowed=0"
echo "$out" | grep -q "VERDICT=EDGE_SCORE_MODEL_V2_PART_2_READY"

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_reconciliation
WHERE source_version='EDGE_SCORE_MODEL_V2_PART_2';
")

if [ "$rows" -lt 1 ]; then
  echo "NO_RECONCILIATION_ROWS"
  exit 1
fi

echo "reconciliation_rows=$rows"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_PART2_OK"
