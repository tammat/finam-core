#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

PLAN_OUT="/tmp/capital_growth_postgresql_schema_plan_v1"
OUT="/tmp/capital_growth_postgresql_schema_revision_v1"
LOG="/tmp/test_capital_growth_postgresql_schema_revision_v1.log"

cd "$ROOT"

echo "=== TEST CAPITAL GROWTH POSTGRESQL SCHEMA REVISION V1 ==="

if [[ ! -f "$PLAN_OUT/columns.tsv" ]]; then
    scripts/research/test_capital_growth_postgresql_schema_plan_v1.sh
fi

rm -rf "$OUT"
rm -f "$LOG"

"$PYTHON" \
  scripts/research/build_capital_growth_postgresql_schema_revision_v1.py |
tee "$LOG"

for file in \
  "$OUT/fk_revision.tsv" \
  "$OUT/nullable_revision.tsv" \
  "$OUT/jsonb_revision.tsv" \
  "$OUT/index_revision.tsv" \
  "$OUT/migration_order_revision.tsv" \
  "$OUT/revised_columns.tsv" \
  "$OUT/revised_constraints.tsv" \
  "$OUT/revision_contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

OUTPUT_VERSION_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $1 == "formula_registry" &&
      $3 == "output_metric_version" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/revised_columns.tsv"
)"

REVISED_FK_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $2 == "fk_formula_output_metric" &&
      index($4, "(output_metric,output_metric_version)") > 0 {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/revised_constraints.tsv"
)"

OLD_COUPLED_FK_COUNT="$(
  {
    grep -F \
      "(output_metric,formula_version)" \
      "$OUT/revised_constraints.tsv" ||
    true
  } |
  wc -l |
  tr -d ' '
)"

UNEXPECTED_NULLABLE_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $4 == "REVIEW_REQUIRED" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/nullable_revision.tsv"
)"

UNAPPROVED_JSONB_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $3 == "REVIEW_REQUIRED" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/jsonb_revision.tsv"
)"

MISSING_FK_INDEX_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $4 == "MISSING_INDEX" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/index_revision.tsv"
)"

INVALID_MIGRATION_ORDER_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $5 == "INVALID" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/migration_order_revision.tsv"
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "output_metric_version_count=$OUTPUT_VERSION_COUNT"
echo "revised_output_metric_fk_count=$REVISED_FK_COUNT"
echo "old_coupled_fk_count=$OLD_COUPLED_FK_COUNT"
echo "unexpected_nullable_count=$UNEXPECTED_NULLABLE_COUNT"
echo "unapproved_jsonb_count=$UNAPPROVED_JSONB_COUNT"
echo "missing_fk_index_count=$MISSING_FK_INDEX_COUNT"
echo "invalid_migration_order_count=$INVALID_MIGRATION_ORDER_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$OUTPUT_VERSION_COUNT" -eq 1 ]]
[[ "$REVISED_FK_COUNT" -eq 1 ]]
[[ "$OLD_COUPLED_FK_COUNT" -eq 0 ]]
[[ "$UNEXPECTED_NULLABLE_COUNT" -eq 0 ]]
[[ "$UNAPPROVED_JSONB_COUNT" -eq 0 ]]
[[ "$MISSING_FK_INDEX_COUNT" -eq 0 ]]
[[ "$INVALID_MIGRATION_ORDER_COUNT" -eq 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

for contract in \
  "MODE=REVISION_ONLY" \
  "DATABASE=POSTGRESQL_ONLY" \
  "FORMULA_METRIC_VERSION_COUPLING=REMOVED" \
  "OUTPUT_METRIC_VERSION_COLUMN=REQUIRED" \
  "APPROVED_NULLABLE_COLUMN_COUNT=2" \
  "APPROVED_JSONB_COLUMN_COUNT=7" \
  "UNRESOLVED_COUNT=0" \
  "DDL_EXECUTED=0" \
  "SCHEMA_CHANGED=0" \
  "DB_WRITES_PERFORMED=0" \
  "RUNTIME_CHANGED=0" \
  "EXECUTION_CHANGED=0" \
  "ORDERS_CHANGED=0" \
  "FILLS_CHANGED=0" \
  "MICRO_LIVE_ALLOWED=0"
do
    grep -Fqx \
      "$contract" \
      "$OUT/revision_contract.txt" || {
          echo "ERROR=contract_missing:$contract"
          exit 1
      }
done

grep -Fq \
  "VERDICT=CAPITAL_GROWTH_POSTGRESQL_SCHEMA_REVISION_V1_READY" \
  "$LOG"

FORBIDDEN_MARKERS=(
  "INSERT INTO"
  "UPDATE "
  "DELETE FROM"
  "TRUNCATE "
  "DROP TABLE"
  "ALTER TABLE"
  "systemctl restart"
  "send_order("
  "place_order("
  "submit_order("
)

for marker in "${FORBIDDEN_MARKERS[@]}"; do
    COUNT="$(
      {
        grep -F "$marker" \
          scripts/research/build_capital_growth_postgresql_schema_revision_v1.py ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_action_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
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

echo "writes_performed=0"
echo "db_writes_performed=0"
echo "ddl_executed=0"
echo "schema_changed=0"
echo "runtime_instrumentation=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "broker_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CAPITAL_GROWTH_POSTGRESQL_SCHEMA_REVISION_V1_OK"
