#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_drift_guard_v2"
REGISTRY_OUT="/tmp/decision_owner_registry_v2"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER DRIFT GUARD V2 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_decision_owner_registry_v2.sh

"$PYTHON" \
  scripts/build_decision_owner_drift_baseline_v2.py

"$PYTHON" \
  scripts/audit_decision_owner_drift_guard_v2.py \
  | tee "$LOG"

FILES=(
  "$OUT/baseline_registry.tsv"
  "$OUT/baseline_edges.tsv"
  "$OUT/baseline_metadata.txt"
  "$OUT/current_registry.tsv"
  "$OUT/current_edges.tsv"
  "$OUT/registry_drift.tsv"
  "$OUT/edge_drift.tsv"
  "$OUT/drift_summary.txt"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

BASELINE_REGISTRY_COUNT="$(
  tail -n +2 "$OUT/baseline_registry.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

CURRENT_REGISTRY_COUNT="$(
  tail -n +2 "$OUT/current_registry.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

BASELINE_EDGE_COUNT="$(
  tail -n +2 "$OUT/baseline_edges.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

CURRENT_EDGE_COUNT="$(
  tail -n +2 "$OUT/current_edges.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

REGISTRY_DRIFT_COUNT="$(
  tail -n +2 "$OUT/registry_drift.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

EDGE_DRIFT_COUNT="$(
  tail -n +2 "$OUT/edge_drift.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "baseline_registry_count=$BASELINE_REGISTRY_COUNT"
echo "current_registry_count=$CURRENT_REGISTRY_COUNT"
echo "baseline_edge_count=$BASELINE_EDGE_COUNT"
echo "current_edge_count=$CURRENT_EDGE_COUNT"
echo "registry_drift_count=$REGISTRY_DRIFT_COUNT"
echo "edge_drift_count=$EDGE_DRIFT_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$BASELINE_REGISTRY_COUNT" -eq 8 ]]
[[ "$CURRENT_REGISTRY_COUNT" -eq 8 ]]
[[ "$BASELINE_EDGE_COUNT" -eq 8 ]]
[[ "$CURRENT_EDGE_COUNT" -eq 8 ]]
[[ "$REGISTRY_DRIFT_COUNT" -eq 0 ]]
[[ "$EDGE_DRIFT_COUNT" -eq 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fq \
  "baseline_commit=a0e421360cece69c2226060c07a2674cdfba4cfb" \
  "$OUT/baseline_metadata.txt"

grep -Fq \
  "strategy_family_scoped=1" \
  "$OUT/baseline_metadata.txt"

grep -Fq \
  "drift_detected=0" \
  "$OUT/drift_summary.txt"

grep -Fq \
  "VERDICT=DECISION_OWNER_DRIFT_GUARD_V2_OK" \
  "$LOG"

# Негативный тест: меняем NG family owner.
sed -i \
  's/NgConservativeBreakoutM1\.on_signal_bar/NgConservativeBreakoutM1.on_signal_bar_v2/' \
  "$REGISTRY_OUT/decision_owner_registry_v2.tsv"

set +e

DECISION_OWNER_DRIFT_SKIP_BUILD=1 \
"$PYTHON" \
  scripts/audit_decision_owner_drift_guard_v2.py \
  > "$OUT/negative_test.log" 2>&1

NEGATIVE_RC=$?

set -e

echo "negative_test_exit_code=$NEGATIVE_RC"
[[ "$NEGATIVE_RC" -eq 1 ]]

grep -Fq \
  "VERDICT=DECISION_OWNER_DRIFT_GUARD_V2_DRIFT_DETECTED" \
  "$OUT/negative_test.log"

grep -Fq \
  "NgConservativeBreakoutM1.on_signal_bar_v2" \
  "$OUT/negative_test.log"

# Восстановление.
"$PYTHON" \
  scripts/build_decision_owner_registry_v2.py \
  >/dev/null

"$PYTHON" \
  scripts/audit_decision_owner_drift_guard_v2.py \
  > "$OUT/final_recheck.log"

grep -Fq \
  "VERDICT=DECISION_OWNER_DRIFT_GUARD_V2_OK" \
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

echo "writes_performed=0"
echo "db_writes_performed=0"
echo "runtime_instrumentation=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "broker_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DECISION_OWNER_DRIFT_GUARD_V2_OK"
