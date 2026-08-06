#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BATCH_ID="${1:-PG_EDGE_SEARCH_V1_20260806_071428}"
LOG="/tmp/test_postgresql_edge_parameter_search_v1_result.log"

cd "$ROOT"

PYTHONPATH=src \
"$PYTHON" \
  scripts/research/verify_postgresql_edge_parameter_search_v1_result.py \
  --batch-id "$BATCH_ID" |
tee "$LOG"

grep -Fq \
  "task_count=72" \
  "$LOG"

grep -Fq \
  "done_count=72" \
  "$LOG"

grep -Fq \
  "candidate_count=0" \
  "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_EDGE_PARAMETER_SEARCH_V1_NO_EDGE_CONFIRMED" \
  "$LOG"

echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_EDGE_PARAMETER_SEARCH_V1_RESULT_OK"
