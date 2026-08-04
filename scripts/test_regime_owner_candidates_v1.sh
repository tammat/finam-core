#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/regime_owner_candidates_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST REGIME OWNER CANDIDATES V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/audit_regime_owner_candidates_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/source_files.tsv"
  "$OUT/regime_functions.tsv"
  "$OUT/regime_constructors.tsv"
  "$OUT/regime_assignments.tsv"
  "$OUT/regime_returns.tsv"
  "$OUT/regime_calls.tsv"
  "$OUT/owner_candidates.tsv"
  "$OUT/excluded_candidates.tsv"
  "$OUT/family_summary.tsv"
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
    "$OUT/owner_candidates.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

OWNER_CANDIDATE_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $16 == "REGIME_OWNER_CANDIDATE" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/owner_candidates.tsv"
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "candidate_count=$CANDIDATE_COUNT"
echo "regime_owner_candidate_count=$OWNER_CANDIDATE_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$UNRESOLVED_COUNT" -eq 0 ]]

# На первом этапе кандидат должен быть найден,
# но владелец ещё не подтверждается.
[[ "$CANDIDATE_COUNT" -gt 0 ]]
[[ "$OWNER_CANDIDATE_COUNT" -gt 0 ]]

PIPELINE_OWNER_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $16 == "REGIME_OWNER_CANDIDATE" &&
      $5 ~ /_on_quote_impl|_record_live_quote_to_storage|_execute_br_signal_in_paper/ {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/owner_candidates.tsv"
)"

echo "pipeline_owner_count=$PIPELINE_OWNER_COUNT"
[[ "$PIPELINE_OWNER_COUNT" -eq 0 ]]

awk -F '\t' '
    NR == 1 {
        next
    }

    $17 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $5
        exit 1
    }

    $18 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $5
        exit 1
    }

    $14 != "0" {
        print "ERROR=side_effect_candidate_not_excluded:" $5
        exit 1
    }
' "$OUT/owner_candidates.tsv"

grep -Fq \
  "confirmed_owner_count=0" \
  "$LOG"

grep -Fq \
  "owner_assignment_performed=0" \
  "$LOG"

grep -Fq \
  "runtime_instrumentation=0" \
  "$LOG"

grep -Fq \
  "VERDICT=REGIME_OWNER_CANDIDATES_V1_READY" \
  "$LOG"

for marker in \
  "INSERT INTO" \
  "UPDATE " \
  "DELETE FROM" \
  "TRUNCATE " \
  "DROP TABLE" \
  "ALTER TABLE" \
  "systemctl restart" \
  "systemctl start" \
  "systemctl stop" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    count="$(
      {
        grep -F "$marker" \
          scripts/audit_regime_owner_candidates_v1.py \
          2>/dev/null ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_action_marker=$marker count=$count"
    [[ "$count" -eq 0 ]]
done

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
echo "VERDICT=TEST_REGIME_OWNER_CANDIDATES_V1_OK"
