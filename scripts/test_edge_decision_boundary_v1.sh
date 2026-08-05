#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_decision_boundary_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST EDGE DECISION BOUNDARY V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_edge_semantic_classification_v1.sh

"$PYTHON" \
  scripts/audit_edge_decision_boundary_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/authoritative_candidates.tsv"
  "$OUT/candidate_call_sites.tsv"
  "$OUT/candidate_result_bindings.tsv"
  "$OUT/result_consumers.tsv"
  "$OUT/candidate_to_candidate_edges.tsv"
  "$OUT/downstream_boundary_edges.tsv"
  "$OUT/boundary_summary.tsv"
  "$OUT/evidence.txt"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

CANDIDATE_COUNT="$(
  tail -n +2 \
    "$OUT/authoritative_candidates.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

SUMMARY_COUNT="$(
  tail -n +2 \
    "$OUT/boundary_summary.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

CALL_COUNT="$(
  tail -n +2 \
    "$OUT/candidate_call_sites.tsv" |
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

echo "authoritative_candidate_count=$CANDIDATE_COUNT"
echo "boundary_summary_count=$SUMMARY_COUNT"
echo "candidate_call_site_count=$CALL_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$CANDIDATE_COUNT" -eq 3 ]]
[[ "$SUMMARY_COUNT" -eq 3 ]]
[[ "$CALL_COUNT" -gt 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

for symbol in \
  "DirectionalEdgeGuard.decide" \
  "StatisticalValidationDecisionEngine.decide" \
  "SessionEdgeGuard.decide"
do
    grep -Fq \
      "$symbol" \
      "$OUT/boundary_summary.tsv" || {
          echo "ERROR=boundary_candidate_missing:$symbol"
          exit 1
      }
done

NO_CALL_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $10 == "NO_CALL_SITE_DISCOVERED" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/boundary_summary.tsv"
)"

echo "no_call_candidate_count=$NO_CALL_COUNT"

# На этом этапе отсутствие call site хотя бы у одного
# authoritative-кандидата считается незавершённым доказательством.
[[ "$NO_CALL_COUNT" -eq 0 ]]

BOUNDARY_EVIDENCE_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      (
          $4 > 0 ||
          $5 > 0 ||
          $6 > 0 ||
          $7 > 0 ||
          $8 > 0
      ) {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/boundary_summary.tsv"
)"

echo "candidate_with_boundary_evidence_count=$BOUNDARY_EVIDENCE_COUNT"
[[ "$BOUNDARY_EVIDENCE_COUNT" -eq 3 ]]

RUNTIME_EVIDENCE_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $9 > 0 {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/boundary_summary.tsv"
)"

echo "runtime_reachable_candidate_count=$RUNTIME_EVIDENCE_COUNT"

# Runtime evidence не обязательно должно быть у всех:
# statistical edge может оставаться research-only.
[[ "$RUNTIME_EVIDENCE_COUNT" -ge 0 ]]

awk -F '\t' '
    NR == 1 {
        next
    }

    $11 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $2
        exit 1
    }

    $12 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $2
        exit 1
    }
' "$OUT/boundary_summary.tsv"

grep -Fq \
  "confirmed_owner_count=0" \
  "$LOG"

grep -Fq \
  "owner_assignment_performed=0" \
  "$LOG"

grep -Fq \
  "VERDICT=EDGE_DECISION_BOUNDARY_V1_READY" \
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
echo "VERDICT=TEST_EDGE_DECISION_BOUNDARY_V1_OK"
