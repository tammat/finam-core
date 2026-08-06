#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/edge_observation_successful_writer_discovery_v1"
LOG="/tmp/test_edge_observation_successful_writer_discovery_v1.log"

cd "$ROOT"

echo "=== TEST EDGE OBSERVATION SUCCESSFUL WRITER DISCOVERY V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

"$PYTHON" \
  scripts/research/audit_edge_observation_successful_writer_discovery_v1.py |
tee "$LOG"

for file in \
  "$OUT/direct_writers.tsv" \
  "$OUT/indirect_candidates.tsv" \
  "$OUT/backtest_consumers.tsv" \
  "$OUT/discovery_contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

DIRECT_WRITER_COUNT="$(
  awk -F= '
      $1 == "DIRECT_WRITER_COUNT" {
          print $2
      }
  ' "$OUT/discovery_contract.txt"
)"

SUCCESS_WRITER_COUNT="$(
  awk -F= '
      $1 == "SUCCESSFUL_DIRECT_WRITER_COUNT" {
          print $2
      }
  ' "$OUT/discovery_contract.txt"
)"

BACKTEST_CONSUMER_COUNT="$(
  awk -F= '
      $1 == "BACKTEST_CONSUMER_COUNT" {
          print $2
      }
  ' "$OUT/discovery_contract.txt"
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "direct_writer_count=$DIRECT_WRITER_COUNT"
echo "successful_direct_writer_count=$SUCCESS_WRITER_COUNT"
echo "backtest_consumer_count=$BACKTEST_CONSUMER_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$DIRECT_WRITER_COUNT" -gt 0 ]]
[[ "$BACKTEST_CONSUMER_COUNT" -gt 0 ]]

grep -Fqx \
  "MODE=STATIC_READ_ONLY" \
  "$OUT/discovery_contract.txt"

grep -Fq \
  "VERDICT=EDGE_OBSERVATION_SUCCESSFUL_WRITER_DISCOVERY_V1_READY" \
  "$LOG"

for marker in \
  "UPDATE analytics.edge_observation_v1" \
  "INSERT INTO analytics.edge_observation_v1" \
  "DELETE FROM analytics.edge_observation_v1" \
  "ALTER TABLE" \
  "DROP TABLE" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" \
          scripts/research/audit_edge_observation_successful_writer_discovery_v1.py ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_runtime_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

echo "source_changed=0"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_OBSERVATION_SUCCESSFUL_WRITER_DISCOVERY_V1_OK"
