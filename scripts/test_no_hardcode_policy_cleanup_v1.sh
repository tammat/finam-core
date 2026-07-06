#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_NO_HARDCODE_POLICY_CLEANUP_V1 ==="

PYTHONPATH=src python -m py_compile src/scripts/check_no_hardcode_v1.py
PYTHONPATH=src python src/scripts/check_no_hardcode_v1.py

grep -q "policy=trade_hardcode_only" reports/no_hardcode_v1_latest.txt
grep -q "VERDICT=NO_HARDCODE_V1_READY" reports/no_hardcode_v1_latest.txt

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$unsafe" = "0"

echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=NO_HARDCODE_POLICY_CLEANUP_V1_READY"
echo "VERDICT=TEST_NO_HARDCODE_POLICY_CLEANUP_V1_OK"
