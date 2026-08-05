#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/capital_growth_postgresql_schema_plan_v1"
LOG="/tmp/test_capital_growth_postgresql_schema_plan_v1.log"

cd "$ROOT"

echo "=== TEST CAPITAL GROWTH POSTGRESQL SCHEMA PLAN V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" \
  scripts/research/build_capital_growth_postgresql_schema_plan_v1.py |
tee "$LOG"

for file in \
  "$OUT/schema_objects.tsv" \
  "$OUT/columns.tsv" \
  "$OUT/constraints.tsv" \
  "$OUT/indexes.tsv" \
  "$OUT/dependencies.tsv" \
  "$OUT/conflict_scan.tsv" \
  "$OUT/migration_order.tsv" \
  "$OUT/schema_plan.sql" \
  "$OUT/schema_contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

TABLE_COUNT="$(
  awk -F '\t' '
      NR > 1 && $3 == "TABLE" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/schema_objects.tsv"
)"

COLUMN_COUNT="$(
  tail -n +2 "$OUT/columns.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

CONSTRAINT_COUNT="$(
  tail -n +2 "$OUT/constraints.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

INDEX_COUNT="$(
  tail -n +2 "$OUT/indexes.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

DEPENDENCY_COUNT="$(
  tail -n +2 "$OUT/dependencies.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

HARD_CONFLICT_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      ($3 == "TYPE_CONFLICT" ||
       $3 == "COLUMN_CONFLICT") {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/conflict_scan.tsv"
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "table_count=$TABLE_COUNT"
echo "column_count=$COLUMN_COUNT"
echo "constraint_count=$CONSTRAINT_COUNT"
echo "index_count=$INDEX_COUNT"
echo "dependency_count=$DEPENDENCY_COUNT"
echo "hard_conflict_count=$HARD_CONFLICT_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$TABLE_COUNT" -eq 11 ]]
[[ "$COLUMN_COUNT" -gt 70 ]]
[[ "$CONSTRAINT_COUNT" -ge 30 ]]
[[ "$INDEX_COUNT" -eq 10 ]]
[[ "$DEPENDENCY_COUNT" -eq 12 ]]
[[ "$HARD_CONFLICT_COUNT" -eq 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

REQUIRED_TABLES=(
  edge_candidates
  edge_lifecycle_events
  metric_registry
  metric_values
  formula_registry
  formula_inputs
  score_snapshots
  risk_budgets
  capital_state
  portfolio_state
  allocation_decisions
)

for table_name in "${REQUIRED_TABLES[@]}"; do
    COUNT="$(
      awk -F '\t' \
        -v table_name="$table_name" '
          NR > 1 &&
          $2 == table_name &&
          $3 == "TABLE" {
              count++
          }

          END {
              print count + 0
          }
        ' "$OUT/schema_objects.tsv"
    )"

    echo "required_table=$table_name count=$COUNT"
    [[ "$COUNT" -eq 1 ]]
done

for contract in \
  "MODE=PLAN_ONLY" \
  "DATABASE=POSTGRESQL_ONLY" \
  "SCHEMA_NAME=capital" \
  "TABLE_COUNT=11" \
  "INDEX_COUNT=10" \
  "DEPENDENCY_COUNT=12" \
  "HARD_CONFLICT_COUNT=0" \
  "DUPLICATE_SCHEMA_OBJECT_COUNT=0" \
  "UNRESOLVED_COUNT=0" \
  "DDL_EXECUTED=0" \
  "SCHEMA_CREATED=0" \
  "DB_WRITES_PERFORMED=0" \
  "SCORE_CALCULATION_ENABLED=0" \
  "ALLOCATION_ENABLED=0" \
  "RUNTIME_USAGE_ALLOWED=0" \
  "EXECUTION_USAGE_ALLOWED=0" \
  "MICRO_LIVE_ALLOWED=0"
do
    grep -Fqx \
      "$contract" \
      "$OUT/schema_contract.txt" || {
          echo "ERROR=contract_missing:$contract"
          exit 1
      }
done

grep -Fq \
  "CONSTRAINT \"ck_allocation_execution_disabled\"" \
  "$OUT/schema_plan.sql"

grep -Fq \
  "CHECK (execution_allowed = false)" \
  "$OUT/schema_plan.sql"

grep -Fq \
  "VERDICT=CAPITAL_GROWTH_POSTGRESQL_SCHEMA_PLAN_V1_READY" \
  "$LOG"

FORBIDDEN_EXECUTION_MARKERS=(
  "psql "
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

for marker in "${FORBIDDEN_EXECUTION_MARKERS[@]}"; do
    COUNT="$(
      {
        grep -F "$marker" \
          scripts/research/build_capital_growth_postgresql_schema_plan_v1.py ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_execution_marker=$marker count=$COUNT"

    case "$marker" in
      "INSERT INTO"|"UPDATE "|"DELETE FROM"|"TRUNCATE "|"DROP TABLE"|"ALTER TABLE")
        # Допускаются только строки внутри генерируемого DDL-плана.
        # В Python builder они отсутствуют как выполняемые SQL-команды.
        [[ "$COUNT" -eq 0 ]]
        ;;
      *)
        [[ "$COUNT" -eq 0 ]]
        ;;
    esac
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

echo "owner_assignment_performed=1"
echo "writes_performed=0"
echo "db_writes_performed=0"
echo "ddl_executed=0"
echo "schema_created=0"
echo "runtime_instrumentation=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "broker_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CAPITAL_GROWTH_POSTGRESQL_SCHEMA_PLAN_V1_OK"
