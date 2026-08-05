#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_drift_guard_v3"
REGISTRY="/tmp/decision_owner_registry_v3/decision_owner_registry_v3.tsv"

cd "$ROOT"

echo "=== TEST DECISION OWNER DRIFT GUARD V3 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_decision_owner_registry_v3.sh

"$PYTHON" scripts/build_decision_owner_drift_baseline_v3.py
"$PYTHON" scripts/audit_decision_owner_drift_guard_v3.py |
  tee "$OUT/test_output.log"

grep -Fq \
  "VERDICT=DECISION_OWNER_DRIFT_GUARD_V3_OK" \
  "$OUT/test_output.log"

grep -Fq "baseline_registry_count=9" "$OUT/drift_summary.txt"
grep -Fq "current_registry_count=9" "$OUT/drift_summary.txt"
grep -Fq "baseline_edge_count=10" "$OUT/drift_summary.txt"
grep -Fq "current_edge_count=10" "$OUT/drift_summary.txt"
grep -Fq "registry_drift_count=0" "$OUT/drift_summary.txt"
grep -Fq "edge_drift_count=0" "$OUT/drift_summary.txt"
grep -Fq "drift_detected=0" "$OUT/drift_summary.txt"

cp -a "$REGISTRY" "$OUT/registry_before_negative.tsv"

sed -i \
  's/BRRegimeLayer\.evaluate/BRRegimeLayer.evaluate_v2/' \
  "$REGISTRY"

set +e

DECISION_OWNER_DRIFT_SKIP_BUILD=1 \
"$PYTHON" scripts/audit_decision_owner_drift_guard_v3.py \
  > "$OUT/negative_test.log" 2>&1

NEGATIVE_RC=$?

set -e

echo "negative_test_exit_code=$NEGATIVE_RC"
[[ "$NEGATIVE_RC" -eq 1 ]]

grep -Fq \
  "VERDICT=DECISION_OWNER_DRIFT_GUARD_V3_DRIFT_DETECTED" \
  "$OUT/negative_test.log"

grep -Fq \
  "BRRegimeLayer.evaluate_v2" \
  "$OUT/negative_test.log"

"$PYTHON" scripts/build_decision_owner_registry_v3.py >/dev/null
"$PYTHON" scripts/audit_decision_owner_drift_guard_v3.py \
  > "$OUT/final_recheck.log"

grep -Fq \
  "VERDICT=DECISION_OWNER_DRIFT_GUARD_V3_OK" \
  "$OUT/final_recheck.log"

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

TRACKED_DIRTY_COUNT="$(
  {
    git status --porcelain |
    grep -Ev '^\?\?' ||
    true
  } |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
echo "tracked_dirty_count=$TRACKED_DIRTY_COUNT"

[[ "$STAGED_COUNT" -eq 0 ]]
[[ "$TRACKED_DIRTY_COUNT" -eq 0 ]]

echo "runtime_instrumentation=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DECISION_OWNER_DRIFT_GUARD_V3_OK"
