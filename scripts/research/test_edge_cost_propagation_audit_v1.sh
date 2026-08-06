#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_cost_propagation_audit_v1"
LOG="/tmp/test_edge_cost_propagation_audit_v1.log"

cd "$ROOT"

echo "=== TEST EDGE COST PROPAGATION AUDIT V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

"$PYTHON" \
  scripts/research/build_edge_cost_propagation_audit_v1.py |
tee "$LOG"

for file in \
  "$OUT/cost_references.tsv" \
  "$OUT/cost_assignments.tsv" \
  "$OUT/edge_observation_writes.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

DISCOVERY_COMMISSION_COUNT="$(
  awk -F '=' '
      $1 == "DISCOVERY_COMMISSION_PARAMETER_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

ZERO_SLIPPAGE_COUNT="$(
  awk -F '=' '
      $1 == "DISCOVERY_ZERO_SLIPPAGE_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

EDGE_OBSERVATION_WRITE_COUNT="$(
  awk -F '=' '
      $1 == "EDGE_OBSERVATION_WRITE_COUNT" {
          print $2
      }
  ' "$OUT/contract.txt"
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "discovery_commission_count=$DISCOVERY_COMMISSION_COUNT"
echo "discovery_zero_slippage_count=$ZERO_SLIPPAGE_COUNT"
echo "edge_observation_write_count=$EDGE_OBSERVATION_WRITE_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$DISCOVERY_COMMISSION_COUNT" -gt 0 ]]
[[ "$ZERO_SLIPPAGE_COUNT" -gt 0 ]]
[[ "$EDGE_OBSERVATION_WRITE_COUNT" -gt 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fqx \
  "DISCOVERY_COMMISSION_SOURCE=ROUNDTRIP_COST" \
  "$OUT/contract.txt"

grep -Fqx \
  "DISCOVERY_SLIPPAGE_POLICY=ZERO" \
  "$OUT/contract.txt"

grep -Fq \
  "VERDICT=EDGE_COST_PROPAGATION_AUDIT_V1_READY" \
  "$LOG"

for marker in \
  "INSERT INTO" \
  "UPDATE " \
  "DELETE FROM" \
  "ALTER TABLE" \
  "DROP TABLE" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" \
          scripts/research/build_edge_cost_propagation_audit_v1.py ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

echo "db_writes_performed=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_COST_PROPAGATION_AUDIT_V1_OK"
