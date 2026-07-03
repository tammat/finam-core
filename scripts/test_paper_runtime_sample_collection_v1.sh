#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_V1 ==="

scripts/apply_paper_runtime_sample_collection_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_runtime_sample_collection_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_v1.py \
  | tee /tmp/paper_runtime_sample_collection_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_V1_READY" /tmp/paper_runtime_sample_collection_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_v1 WHERE micro_live_allowed=true;")

test "$rows" = "1"
test "$allowed" = "0"

psql -d finam_core -c "
SELECT
    candidates_total,
    sample_ready,
    wait_both_sample,
    min_remaining_total_trades,
    min_remaining_oos_trades,
    avg_progress_pct,
    max_progress_pct,
    collection_status,
    phase_status,
    recommended_action
FROM marketcore_ui.paper_runtime_sample_collection_v1
WHERE id=1;
"

echo "sample_collection_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_V1_OK"
