#!/usr/bin/env bash
set -euo pipefail

FILE="src/scripts/build_microstructure_health_v1.py"
LOG="runtime/audits/microstructure_health_latest_query_v1.log"

echo "=== TEST_MICROSTRUCTURE_HEALTH_LATEST_QUERY_V1 ==="

[[ -f "$FILE" ]] || {
    echo "ERROR=source_file_missing"
    exit 1
}

mkdir -p runtime/audits

PYTHONPATH=src python -m py_compile "$FILE"

python3 - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/build_microstructure_health_v1.py"
).read_text(encoding="utf-8")

required = [
    "observed_at AS last_observed_at",
    "exchange_ts AS last_exchange_ts",
    "ORDER BY observed_at DESC",
    "LIMIT 1",
]

for item in required:
    if item not in text:
        raise SystemExit(f"ERROR=required_sql_missing:{item}")

forbidden = [
    "SELECT max(observed_at) AS last_observed_at,max(exchange_ts)",
    "SELECT max(observed_at) AS last_observed_at, max(exchange_ts)",
]

for item in forbidden:
    if item in text:
        raise SystemExit("ERROR=legacy_full_history_aggregate_remains")

print("source_contract=OK")
PY

PLAN="$(
    psql -X -d finam_core -Atqc "
    EXPLAIN
    SELECT
        observed_at AS last_observed_at,
        exchange_ts AS last_exchange_ts
    FROM analytics.market_microstructure_snapshot_v1
    WHERE symbol='BRQ6@RTSX'
    ORDER BY observed_at DESC
    LIMIT 1;
    "
)"

printf '%s\n' "$PLAN"

grep -q \
  "idx_market_microstructure_symbol_observed_v1" \
  <<<"$PLAN" || {
    echo "ERROR=expected_index_not_used"
    exit 1
}

set +e
/opt/finam-core/.venv/bin/python \
  "$FILE" >"$LOG" 2>&1
rc=$?
set -e

if [[ "$rc" -ne 0 ]]; then
    echo "ERROR=builder_return_code_$rc"
    tail -100 "$LOG"
    exit "$rc"
fi

grep -q \
  "VERDICT=MICROSTRUCTURE_HEALTH_V1_OK" \
  "$LOG" || {
    echo "ERROR=builder_verdict_missing"
    tail -100 "$LOG"
    exit 1
}

echo "log_file=$LOG"
echo "VERDICT=TEST_MICROSTRUCTURE_HEALTH_LATEST_QUERY_V1_OK"
exit 0
