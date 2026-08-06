#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/capital_growth_edge_inventory_v1"
LOG="/tmp/test_capital_growth_edge_inventory_v1.log"

cd "$ROOT"

echo "=== TEST CAPITAL GROWTH EDGE INVENTORY V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" \
  scripts/research/build_capital_growth_edge_inventory_v1.py |
tee "$LOG"

for file in \
  "$OUT/candidate_relations.tsv" \
  "$OUT/candidate_columns.tsv" \
  "$OUT/candidate_rows.tsv" \
  "$OUT/source_coverage.tsv" \
  "$OUT/inventory_contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

RELATION_COUNT="$(
  tail -n +2 "$OUT/candidate_relations.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

CANDIDATE_ROW_COUNT="$(
  tail -n +2 "$OUT/candidate_rows.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "candidate_relation_count=$RELATION_COUNT"
echo "candidate_row_count=$CANDIDATE_ROW_COUNT"

# Нулевой результат допустим как диагностический факт,
# но файлы и контракт обязаны существовать.
[[ "$RELATION_COUNT" -ge 0 ]]
[[ "$CANDIDATE_ROW_COUNT" -ge 0 ]]

for contract in \
  "MODE=READ_ONLY_DISCOVERY" \
  "DATABASE=POSTGRESQL_ONLY" \
  "DB_WRITES_PERFORMED=0" \
  "STRATEGY_CHANGED=0" \
  "RISK_ENGINE_CHANGED=0" \
  "RUNTIME_CHANGED=0" \
  "EXECUTION_CHANGED=0" \
  "ORDERS_CHANGED=0" \
  "FILLS_CHANGED=0" \
  "MICRO_LIVE_ALLOWED=0"
do
    grep -Fqx \
      "$contract" \
      "$OUT/inventory_contract.txt" || {
          echo "ERROR=contract_missing:$contract"
          exit 1
      }
done

grep -Fq \
  "VERDICT=CAPITAL_GROWTH_EDGE_INVENTORY_V1_READY" \
  "$LOG"

FORBIDDEN_MARKERS=(
  "INSERT INTO"
  "UPDATE "
  "DELETE FROM"
  "TRUNCATE "
  "DROP TABLE"
  "ALTER TABLE"
  "CREATE TABLE"
  "CREATE SCHEMA"
  "send_order("
  "place_order("
  "submit_order("
)

for marker in "${FORBIDDEN_MARKERS[@]}"; do
    COUNT="$(
      {
        grep -F "$marker" \
          scripts/research/build_capital_growth_edge_inventory_v1.py ||
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
echo "runtime_instrumentation=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "broker_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CAPITAL_GROWTH_EDGE_INVENTORY_V1_OK"
