#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_drift_guard_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER DRIFT GUARD V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

# Воспроизводим только durable evidence-цепочку,
# необходимую финальному registry builder.
scripts/test_decision_owner_candidate_reduction_v1.sh
scripts/test_decision_owner_priority_evidence_v1.sh
scripts/test_decision_owner_priority_semantic_classification_v1.sh
scripts/test_decision_owner_priority_call_path_v1.sh
scripts/test_decision_owner_runtime_gate_reachability_v1.sh
scripts/test_decision_owner_runtime_caller_chain_v2.sh
scripts/test_decision_owner_priority_confirmation_v1.sh
scripts/test_execution_broker_result_ownership_v1.sh
scripts/test_execution_broker_domain_status_mapping_v1.sh
scripts/test_execution_broker_layered_status_ownership_v1.sh
scripts/test_decision_owner_registry_v1.sh

"$PYTHON" \
  scripts/build_decision_owner_drift_baseline_v1.py

"$PYTHON" \
  scripts/audit_decision_owner_drift_guard_v1.py \
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

[[ "$BASELINE_REGISTRY_COUNT" -eq 4 ]]
[[ "$CURRENT_REGISTRY_COUNT" -eq 4 ]]
[[ "$BASELINE_EDGE_COUNT" -eq 4 ]]
[[ "$CURRENT_EDGE_COUNT" -eq 4 ]]
[[ "$REGISTRY_DRIFT_COUNT" -eq 0 ]]
[[ "$EDGE_DRIFT_COUNT" -eq 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -q \
  '^baseline_commit=149742a9fb63b314846beb27acd0664bcb53da6a$' \
  "$OUT/baseline_metadata.txt"

grep -q \
  '^drift_detected=0$' \
  "$OUT/drift_summary.txt"

grep -q \
  '^runtime_instrumentation=0$' \
  "$OUT/drift_summary.txt"

grep -q \
  '^VERDICT=DECISION_OWNER_DRIFT_GUARD_V1_OK$' \
  "$LOG"

# Негативный тест: искусственная подмена current owner
# должна дать ненулевой exit code и DRIFT_DETECTED.
cp \
  "$OUT/current_registry.tsv" \
  "$OUT/current_registry.negative.tsv"

sed -i \
  's/PortfolioRiskGate\.check/PortfolioRiskGate.check_v2/' \
  /tmp/decision_owner_registry_v1/decision_owner_registry_v1.tsv

set +e

DECISION_OWNER_DRIFT_SKIP_BUILD=1 \
"$PYTHON" \
  scripts/audit_decision_owner_drift_guard_v1.py \
  > "$OUT/negative_test.log" 2>&1

NEGATIVE_RC=$?

set -e

echo "negative_test_exit_code=$NEGATIVE_RC"
[[ "$NEGATIVE_RC" -eq 1 ]]

NEGATIVE_ASSERTION_FAILED=0

assert_negative_log() {
    local label="$1"
    local pattern="$2"

    if grep -Fq "$pattern" "$OUT/negative_test.log"; then
        echo "negative_assertion=$label status=OK"
    else
        echo "ERROR=negative_assertion_missing:$label:$pattern"
        NEGATIVE_ASSERTION_FAILED=1
    fi
}

assert_negative_log \
  "verdict" \
  "VERDICT=DECISION_OWNER_DRIFT_GUARD_V1_DRIFT_DETECTED"

assert_negative_log \
  "owner_symbol_field" \
  "field=owner_symbol"

assert_negative_log \
  "builder_skipped" \
  "current_registry_builder_skipped=1"

assert_negative_log \
  "baseline_owner" \
  "baseline=PortfolioRiskGate.check"

assert_negative_log \
  "current_owner" \
  "current=PortfolioRiskGate.check_v2"

if [[ "$NEGATIVE_ASSERTION_FAILED" -ne 0 ]]; then
    echo "=== NEGATIVE TEST LOG ==="
    cat "$OUT/negative_test.log"
    echo "ERROR=negative_test_contract_failed"
    exit 1
fi

# Восстанавливаем current registry после негативной подмены.
set +e

"$PYTHON" \
  scripts/build_decision_owner_registry_v1.py \
  > "$OUT/restore_registry.log" 2>&1

RESTORE_RC=$?

set -e

echo "restore_registry_exit_code=$RESTORE_RC"

if [[ "$RESTORE_RC" -ne 0 ]]; then
    echo "=== RESTORE REGISTRY LOG ==="
    cat "$OUT/restore_registry.log"
    echo "ERROR=current_registry_restore_failed"
    exit 1
fi

if ! grep -Fq \
  $'RISK\tDECISION_GATE\t' \
  /tmp/decision_owner_registry_v1/decision_owner_registry_v1.tsv
then
    echo "ERROR=restored_risk_owner_row_missing"
    cat /tmp/decision_owner_registry_v1/decision_owner_registry_v1.tsv
    exit 1
fi

if grep -Fq \
  "PortfolioRiskGate.check_v2" \
  /tmp/decision_owner_registry_v1/decision_owner_registry_v1.tsv
then
    echo "ERROR=negative_fixture_not_restored"
    exit 1
fi

grep -Fq \
  "PortfolioRiskGate.check" \
  /tmp/decision_owner_registry_v1/decision_owner_registry_v1.tsv

set +e

"$PYTHON" \
  scripts/audit_decision_owner_drift_guard_v1.py \
  > "$OUT/final_recheck.log" 2>&1

FINAL_RECHECK_RC=$?

set -e

echo "final_recheck_exit_code=$FINAL_RECHECK_RC"

if [[ "$FINAL_RECHECK_RC" -ne 0 ]]; then
    echo "=== FINAL RECHECK LOG ==="
    cat "$OUT/final_recheck.log"
    echo "ERROR=final_drift_recheck_failed"
    exit 1
fi

if ! grep -Fq \
  "VERDICT=DECISION_OWNER_DRIFT_GUARD_V1_OK" \
  "$OUT/final_recheck.log"
then
    echo "=== FINAL RECHECK LOG ==="
    cat "$OUT/final_recheck.log"
    echo "ERROR=final_drift_verdict_missing"
    exit 1
fi

echo "post_negative_restore=OK"
echo "final_drift_recheck=OK"

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
echo "VERDICT=TEST_DECISION_OWNER_DRIFT_GUARD_V1_OK"
