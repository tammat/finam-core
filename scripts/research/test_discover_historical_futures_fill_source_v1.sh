#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
DISCOVERY="scripts/research/discover_historical_futures_fill_source_v1.py"
LOG="/tmp/test_discover_historical_futures_fill_source_v1.log"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$DISCOVERY"

set +e

PYTHONPATH=src \
"$PYTHON" "$DISCOVERY" |
tee "$LOG"

RC="${PIPESTATUS[0]}"

set -e

echo "discovery_exit_code=$RC"

grep -Fq "candidate_count=" "$LOG"
grep -Fq "usable_candidate_count=" "$LOG"

for marker in \
  "INSERT INTO" \
  "UPDATE " \
  "DELETE FROM" \
  "send_order(" \
  "place_order(" \
  "submit_order(" \
  "sqlite3" \
  "bars.sqlite"
do
    COUNT="$(
      {
        grep -F "$marker" "$DISCOVERY" ||
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

if [[ "$RC" -eq 0 ]]; then
    grep -Fq \
      "VERDICT=HISTORICAL_FUTURES_FILL_SOURCE_V1_READY" \
      "$LOG"

    echo "VERDICT=TEST_HISTORICAL_FUTURES_FILL_SOURCE_V1_READY"
    exit 0
fi

if [[ "$RC" -eq 2 ]]; then
    grep -Fq \
      "VERDICT=HISTORICAL_FUTURES_FILL_SOURCE_V1_NOT_FOUND" \
      "$LOG"

    echo "VERDICT=TEST_HISTORICAL_FUTURES_FILL_SOURCE_V1_NOT_FOUND_CONFIRMED"
    exit 0
fi

echo "VERDICT=TEST_HISTORICAL_FUTURES_FILL_SOURCE_V1_FAILED"
exit "$RC"
