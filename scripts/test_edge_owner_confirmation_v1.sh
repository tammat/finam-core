#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_owner_confirmation_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST EDGE OWNER CONFIRMATION V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_edge_dormant_component_classification_v1.sh

"$PYTHON" \
  scripts/build_edge_owner_confirmation_v1.py \
  | tee "$LOG"

for file in \
  "$OUT/confirmed_edge_owners.tsv" \
  "$OUT/deferred_edge_stage.tsv" \
  "$OUT/dormant_edge_components.tsv" \
  "$OUT/edge_owner_confirmation_contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

CONFIRMED_COUNT="$(
  tail -n +2 \
    "$OUT/confirmed_edge_owners.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

DORMANT_COUNT="$(
  tail -n +2 \
    "$OUT/dormant_edge_components.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

DEFERRED_COUNT="$(
  tail -n +2 \
    "$OUT/deferred_edge_stage.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

UNRESOLVED_COUNT="$(
  tail -n +2 \
    "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "confirmed_edge_owner_count=$CONFIRMED_COUNT"
echo "dormant_edge_component_count=$DORMANT_COUNT"
echo "deferred_edge_stage_count=$DEFERRED_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$CONFIRMED_COUNT" -eq 0 ]]
[[ "$DORMANT_COUNT" -eq 3 ]]
[[ "$DEFERRED_COUNT" -eq 1 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

for symbol in \
  "DirectionalEdgeGuard.decide" \
  "StatisticalValidationDecisionEngine.decide" \
  "SessionEdgeGuard.decide"
do
    grep -Fq \
      "$symbol" \
      "$OUT/dormant_edge_components.tsv" || {
          echo "ERROR=dormant_component_missing:$symbol"
          exit 1
      }
done

DORMANT_CLASS_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $5 == "DORMANT_EDGE_DECISION_COMPONENT" &&
      $6 == "NOT_OWNER" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/dormant_edge_components.tsv"
)"

echo "dormant_not_owner_count=$DORMANT_CLASS_COUNT"
[[ "$DORMANT_CLASS_COUNT" -eq 3 ]]

grep -Fq \
  $'EDGE\tEDGE_DECISION\tDEFERRED\t0\t3\t\t\t' \
  "$OUT/deferred_edge_stage.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $4 != "0" {
        print "ERROR=edge_owner_count_invalid"
        exit 1
    }

    $5 != "3" {
        print "ERROR=dormant_component_count_invalid"
        exit 1
    }

    $9 != "0" {
        print "ERROR=deferred_owner_confirmed"
        exit 1
    }

    $10 != "0" {
        print "ERROR=runtime_instrumentation_enabled"
        exit 1
    }
' "$OUT/deferred_edge_stage.tsv"

for contract in \
  "CONFIRMATION_RESULT=NO_OWNER_CONFIRMED" \
  "EDGE_STAGE_STATUS=DEFERRED" \
  "EDGE_OWNER=DEFERRED" \
  "CONFIRMED_EDGE_OWNER_COUNT=0" \
  "DORMANT_EDGE_COMPONENT_COUNT=3" \
  "DEFERRED_EDGE_STAGE_COUNT=1" \
  "UNRESOLVED_COUNT=0" \
  "OWNER_ASSIGNMENT_PERFORMED=1" \
  "RUNTIME_INSTRUMENTATION=0" \
  "MICRO_LIVE_ALLOWED=0"
do
    grep -Fq \
      "$contract" \
      "$OUT/edge_owner_confirmation_contract.txt" || {
          echo "ERROR=contract_missing:$contract"
          exit 1
      }
done

grep -Fq \
  "VERDICT=EDGE_OWNER_CONFIRMATION_V1_READY" \
  "$LOG"

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

echo "owner_assignment_performed=1"
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
echo "VERDICT=TEST_EDGE_OWNER_CONFIRMATION_V1_OK"
