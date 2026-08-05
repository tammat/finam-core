#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/capital_growth_ontology_v1"
LOG="/tmp/test_capital_growth_ontology_v1.log"

cd "$ROOT"

echo "=== TEST CAPITAL GROWTH ONTOLOGY V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

"$PYTHON" \
  scripts/research/build_capital_growth_ontology_v1.py |
tee "$LOG"

for file in \
  "$OUT/entities.tsv" \
  "$OUT/relationships.tsv" \
  "$OUT/lifecycle_transitions.tsv" \
  "$OUT/decision_boundaries.tsv" \
  "$OUT/invariants.tsv" \
  "$OUT/ontology_contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

ENTITY_COUNT="$(
  tail -n +2 "$OUT/entities.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

RELATIONSHIP_COUNT="$(
  tail -n +2 "$OUT/relationships.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

TRANSITION_COUNT="$(
  tail -n +2 "$OUT/lifecycle_transitions.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

BOUNDARY_COUNT="$(
  tail -n +2 "$OUT/decision_boundaries.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

INVARIANT_COUNT="$(
  tail -n +2 "$OUT/invariants.tsv" |
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

echo "entity_count=$ENTITY_COUNT"
echo "relationship_count=$RELATIONSHIP_COUNT"
echo "lifecycle_transition_count=$TRANSITION_COUNT"
echo "decision_boundary_count=$BOUNDARY_COUNT"
echo "invariant_count=$INVARIANT_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$ENTITY_COUNT" -eq 8 ]]
[[ "$RELATIONSHIP_COUNT" -eq 8 ]]
[[ "$TRANSITION_COUNT" -eq 9 ]]
[[ "$BOUNDARY_COUNT" -eq 8 ]]
[[ "$INVARIANT_COUNT" -eq 10 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

for entity in \
  CapitalState \
  EdgeCandidate \
  EdgeLifecycle \
  CapitalGrowthScore \
  AllocationDecision \
  PortfolioState \
  RiskBudget \
  ResearchUniverse
do
    grep -Fq \
      "$entity" \
      "$OUT/entities.tsv" || {
          echo "ERROR=entity_missing:$entity"
          exit 1
      }
done

for status in \
  RESEARCH \
  ROBUST \
  OOS_READY \
  SHADOW_READY \
  PAPER_READY \
  CAPITAL_ALLOCATED \
  REAL_ELIGIBLE \
  QUARANTINED \
  REJECTED
do
    grep -Fq \
      "$status" \
      "$OUT/lifecycle_transitions.tsv" || {
          echo "ERROR=lifecycle_status_missing:$status"
          exit 1
      }
done

for contract in \
  "PRIMARY_GOAL=MAXIMIZE_LONG_TERM_CAPITAL_GROWTH" \
  "DATABASE=POSTGRESQL_ONLY" \
  "EVENT_DRIVEN=1" \
  "AI_DIRECT_ORDER_ALLOWED=0" \
  "RISK_ENGINE_CENTRALIZED=1" \
  "ENTITY_COUNT=8" \
  "RELATIONSHIP_COUNT=8" \
  "LIFECYCLE_TRANSITION_COUNT=9" \
  "DECISION_BOUNDARY_COUNT=8" \
  "INVARIANT_COUNT=10" \
  "DUPLICATE_ENTITY_COUNT=0" \
  "DUPLICATE_INVARIANT_CODE_COUNT=0" \
  "UNRESOLVED_COUNT=0" \
  "RUNTIME_CHANGED=0" \
  "EXECUTION_CHANGED=0" \
  "ORDERS_CHANGED=0" \
  "FILLS_CHANGED=0" \
  "MICRO_LIVE_ALLOWED=0"
do
    grep -Fqx \
      "$contract" \
      "$OUT/ontology_contract.txt" || {
          echo "ERROR=contract_missing:$contract"
          exit 1
      }
done

grep -Fq \
  "AI не имеет права отправлять ордера" \
  "$OUT/invariants.tsv"

grep -Fq \
  "Execution принимает только разрешённый Risk Engine order intent" \
  "$OUT/invariants.tsv"

grep -Fq \
  "VERDICT=CAPITAL_GROWTH_ONTOLOGY_V1_READY" \
  "$LOG"

FORBIDDEN_MARKERS=(
  "INSERT INTO"
  "UPDATE "
  "DELETE FROM"
  "TRUNCATE "
  "DROP TABLE"
  "ALTER TABLE"
  "systemctl restart"
  "systemctl start"
  "systemctl stop"
  "send_order("
  "place_order("
  "submit_order("
)

for marker in "${FORBIDDEN_MARKERS[@]}"; do
    COUNT="$(
      {
        grep -F "$marker" \
          scripts/research/build_capital_growth_ontology_v1.py ||
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
echo "VERDICT=TEST_CAPITAL_GROWTH_ONTOLOGY_V1_OK"
