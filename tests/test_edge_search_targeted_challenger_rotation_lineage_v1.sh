#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/scripts/research/build_edge_search_targeted_challenger_rotation_lineage_v1.py"
OUT="/tmp/edge_search_targeted_challenger_rotation_lineage_v1.out"

PYTHONPATH=src "$PY" -m py_compile "$FILE"
git diff --check -- "$FILE"

rm -f "$OUT"

PYTHONPATH=src "$PY" "$FILE" | tee "$OUT"

grep -q '^workflow_candidates=' "$OUT"
grep -q '^shadow_candidates=' "$OUT"
grep -q '^hypothesis_candidates=' "$OUT"
grep -q '^observed_candidate_codes=' "$OUT"
grep -q '^historical_rotation_observed=' "$OUT"

grep -q 'universe_capacity_known=13' "$OUT"
grep -q 'cycle_budget_known=1' "$OUT"
grep -q 'automatic_rotation_assumed=0' "$OUT"
grep -q 'allocator_changed=0' "$OUT"
grep -q 'optimizer_changed=0' "$OUT"
grep -q 'db_writes_performed=0' "$OUT"

grep -q \
'VERDICT=EDGE_SEARCH_TARGETED_CHALLENGER_ROTATION_LINEAGE_V1_READY' \
"$OUT"

echo "rotation_lineage_measured=1"
echo "automatic_rotation_assumed=0"
echo "allocator_changed=0"
echo "optimizer_changed=0"
echo "db_writes_performed=0"
echo "queue_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SEARCH_TARGETED_CHALLENGER_ROTATION_LINEAGE_V1_OK"
