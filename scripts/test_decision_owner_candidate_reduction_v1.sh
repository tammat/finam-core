#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_candidate_reduction_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER CANDIDATE REDUCTION V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/audit_decision_owner_candidate_reduction_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/reduced_candidates.tsv"
  "$OUT/excluded_candidates.tsv"
  "$OUT/stage_summary.tsv"
  "$OUT/unresolved_stages.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

STAGE_COUNT="$(
  tail -n +2 "$OUT/stage_summary.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "stage_count=$STAGE_COUNT"
[[ "$STAGE_COUNT" -eq 10 ]]

# На этом этапе владельцы не назначаются.
awk -F '\t' '
    {
        for (column = 1; column <= NF; column++) {
            sub(/\r$/, "", $column)
        }
    }

    NR == 1 {
        next
    }

    $6 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $1
        exit 1
    }

    $7 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $1
        exit 1
    }
' "$OUT/stage_summary.tsv"

# Presentation/API/Read Model не могут попасть в manual review.
if awk -F '\t' '
    NR == 1 {
        next
    }

    $4 ~ /^src\/marketcore\/api\// ||
    $4 ~ /^src\/marketcore\/presentation\// {
        print "ERROR=read_model_candidate_not_excluded:" $4
        exit 1
    }
' "$OUT/reduced_candidates.tsv"
then
    :
else
    exit 1
fi

# Каждый оставленный кандидат должен быть из product runtime namespace.
awk -F '\t' '
    NR == 1 {
        next
    }

    $4 !~ /^src\/finam_core\/(pipelines|strategy|regime|risk|portfolio|runtime|execution|adapters)\// {
        print "ERROR=non_product_candidate:" $4
        exit 1
    }

    $7 != "CANDIDATE_FOR_MANUAL_REVIEW" {
        print "ERROR=unexpected_reduced_classification:" $7
        exit 1
    }

    $14 != "0" || $15 != "0" {
        print "ERROR=authority_or_runtime_enabled:" $1
        exit 1
    }
' "$OUT/reduced_candidates.tsv"

grep -q '^confirmed_owner_count=0$' "$LOG"
grep -q '^owner_assignment_performed=0$' "$LOG"
grep -q '^runtime_instrumentation=0$' "$LOG"
grep -q \
  '^VERDICT=DECISION_OWNER_CANDIDATE_REDUCTION_V1_READY$' \
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
          scripts/audit_decision_owner_candidate_reduction_v1.py \
          2>/dev/null || true
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

echo "staged_count=$STAGED_COUNT"
[[ "$STAGED_COUNT" -eq 0 ]]

echo "owner_assignment_performed=0"
echo "writes_performed=0"
echo "db_writes_performed=0"
echo "runtime_instrumentation=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DECISION_OWNER_CANDIDATE_REDUCTION_V1_OK"
