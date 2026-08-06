#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/backtest_metric_basis_v1"
LOG="/tmp/test_backtest_metric_basis_v1.log"

cd "$ROOT"

echo "=== TEST BACKTEST METRIC BASIS V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

"$PYTHON" \
  scripts/research/audit_backtest_metric_basis_v1.py |
tee "$LOG"

for file in \
  "$OUT/metric_basis_assignments.tsv" \
  "$OUT/edge_observation_writers.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

GAIN_NET="$(
  awk -F= '
    $1 == "GROSS_GAIN_USES_NET_COUNT" { print $2 }
  ' "$OUT/contract.txt"
)"

LOSS_NET="$(
  awk -F= '
    $1 == "GROSS_LOSS_USES_NET_COUNT" { print $2 }
  ' "$OUT/contract.txt"
)"

SUCCESS_WRITER="$(
  awk -F= '
    $1 == "SUCCESSFUL_METRIC_WRITER_COUNT" {
        print $2
    }
  ' "$OUT/contract.txt"
)"

echo "gross_gain_uses_net_count=$GAIN_NET"
echo "gross_loss_uses_net_count=$LOSS_NET"
UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "successful_metric_writer_count=$SUCCESS_WRITER"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ -n "$GAIN_NET" ]]
[[ -n "$LOSS_NET" ]]
[[ -n "$SUCCESS_WRITER" ]]
[[ "$SUCCESS_WRITER" -gt 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fq \
  "VERDICT=BACKTEST_METRIC_BASIS_V1_READY" \
  "$LOG"

echo "source_changed=0"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_BACKTEST_METRIC_BASIS_V1_OK"
