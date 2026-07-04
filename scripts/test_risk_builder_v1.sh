#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_BUILDER_V1 ==="

PYTHONPATH=src python -m py_compile \
    src/risk/base/aggregator.py \
    src/scripts/build_risk_builder_v1.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/build_risk_builder_v1.py \
| tee /tmp/risk_builder_v1.txt

grep -q "VERDICT=RISK_BUILDER_V1_READY" \
    /tmp/risk_builder_v1.txt

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.risk_decision_snapshot_v1;
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.risk_decision_snapshot_v1
WHERE ready_for_live=true;
")

test "$rows" -gt 0
test "$unsafe" = "0"

echo "risk_rows=$rows"
echo "unsafe_live_rows=$unsafe"

echo "VERDICT=TEST_RISK_BUILDER_V1_OK"
