#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_cost_join_contract_audit_v1"
LOG="/tmp/test_edge_cost_join_contract_audit_v1.log"

cd "$ROOT"

rm -rf "$OUT"
rm -f "$LOG"

echo "=== TEST EDGE COST JOIN CONTRACT AUDIT V1 ==="

PYTHONPATH=src \
"$PYTHON" \
  scripts/research/build_edge_cost_join_contract_audit_v1.py |
tee "$LOG"

for file in \
  "$OUT/observation_keys.tsv" \
  "$OUT/trade_keys.tsv" \
  "$OUT/join_cardinality.tsv" \
  "$OUT/oos_cardinality.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

SAFE_JOIN_COUNT="$(
  awk -F '\t' '
      NR > 1 && $16 == "JOIN_SAFE" { count++ }
      END { print count + 0 }
  ' "$OUT/join_cardinality.tsv"
)"

UNSAFE_JOIN_COUNT="$(
  awk -F '\t' '
      NR > 1 && $16 != "JOIN_SAFE" { count++ }
      END { print count + 0 }
  ' "$OUT/join_cardinality.tsv"
)"

AMBIGUOUS_OOS_COUNT="$(
  awk -F '\t' '
      NR > 1 && $9 != "UNIQUE_CURRENT_ROW" { count++ }
      END { print count + 0 }
  ' "$OUT/oos_cardinality.tsv"
)"

echo "safe_join_count=$SAFE_JOIN_COUNT"
echo "unsafe_join_count=$UNSAFE_JOIN_COUNT"
echo "ambiguous_oos_count=$AMBIGUOUS_OOS_COUNT"

grep -Fqx "MODE=READ_ONLY" "$OUT/contract.txt"
grep -Fqx "DATABASE=POSTGRESQL_ONLY" "$OUT/contract.txt"
grep -Fqx "PARAMETER_HASH_PRESENT_IN_TRADES=0" "$OUT/contract.txt"
grep -Fqx "MARKET_REGIME_PRESENT_IN_TRADES=0" "$OUT/contract.txt"
grep -Fqx "DB_WRITES_PERFORMED=0" "$OUT/contract.txt"

grep -Fq \
  "VERDICT=EDGE_COST_JOIN_CONTRACT_AUDIT_V1_READY" \
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
          scripts/research/build_edge_cost_join_contract_audit_v1.py ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_COST_JOIN_CONTRACT_AUDIT_V1_OK"
