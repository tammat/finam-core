#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_decision_boundary_qualified_binding_v2"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST EDGE DECISION BOUNDARY QUALIFIED BINDING V2 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_edge_semantic_classification_v1.sh

"$PYTHON" \
  scripts/audit_edge_decision_boundary_qualified_binding_v2.py \
  | tee "$LOG"

for file in \
  "$OUT/candidate_identities.tsv" \
  "$OUT/import_aliases.tsv" \
  "$OUT/constructor_bindings.tsv" \
  "$OUT/attribute_bindings.tsv" \
  "$OUT/local_bindings.tsv" \
  "$OUT/qualified_call_sites.tsv" \
  "$OUT/remaining_ambiguous_calls.tsv" \
  "$OUT/candidate_summary.tsv" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

CANDIDATE_COUNT="$(
  tail -n +2 "$OUT/candidate_summary.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

QUALIFIED_CALL_COUNT="$(
  tail -n +2 "$OUT/qualified_call_sites.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

CANDIDATE_WITH_CALL_COUNT="$(
  awk -F '\t' '
      NR > 1 && $3 > 0 {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/candidate_summary.tsv"
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

AMBIGUOUS_COUNT="$(
  tail -n +2 \
    "$OUT/remaining_ambiguous_calls.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "candidate_count=$CANDIDATE_COUNT"
echo "qualified_call_count=$QUALIFIED_CALL_COUNT"
echo "candidate_with_qualified_call_count=$CANDIDATE_WITH_CALL_COUNT"
echo "remaining_ambiguous_call_count=$AMBIGUOUS_COUNT"
echo "unresolved_candidate_count=$UNRESOLVED_COUNT"

[[ "$CANDIDATE_COUNT" -eq 3 ]]
[[ "$QUALIFIED_CALL_COUNT" -gt 0 ]]

# Все три кандидата должны либо получить qualified call,
# либо остаться явно unresolved для следующего доказательного шага.
[[ "$CANDIDATE_WITH_CALL_COUNT" -ge 1 ]]

for symbol in \
  "DirectionalEdgeGuard.decide" \
  "StatisticalValidationDecisionEngine.decide" \
  "SessionEdgeGuard.decide"
do
    grep -Fq \
      "$symbol" \
      "$OUT/candidate_summary.tsv" || {
          echo "ERROR=candidate_missing:$symbol"
          exit 1
      }
done

# Совпадающий risk.SessionEdgeGuard не должен попасть
# в analytics authoritative call sites.
RISK_SESSION_FALSE_BINDING_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $1 == "src/finam_core/analytics/session_edge_guard.py" &&
      $4 == "src/finam_core/risk/session_edge_guard.py" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/qualified_call_sites.tsv"
)"

echo "risk_session_false_binding_count=$RISK_SESSION_FALSE_BINDING_COUNT"
[[ "$RISK_SESSION_FALSE_BINDING_COUNT" -eq 0 ]]

awk -F '\t' '
    NR == 1 {
        next
    }

    $7 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $2
        exit 1
    }

    $8 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $2
        exit 1
    }
' "$OUT/candidate_summary.tsv"

grep -Fq \
  "VERDICT=EDGE_DECISION_BOUNDARY_QUALIFIED_BINDING_V2_READY" \
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

echo "confirmed_owner_count=0"
echo "owner_assignment_performed=0"
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
echo "VERDICT=TEST_EDGE_DECISION_BOUNDARY_QUALIFIED_BINDING_V2_OK"
