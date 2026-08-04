#!/usr/bin/env bash
set -euo pipefail

FILE="src/scripts/run_moex_index_online_v2.py"

echo "=== TEST_MOEX_INDEX_ONLINE_FAST_STATE_V1 ==="

[[ -f "$FILE" ]] || {
    echo "ERROR=source_file_missing"
    exit 1
}

PYTHONPATH=src python -m py_compile "$FILE"

python3 - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/run_moex_index_online_v2.py"
).read_text(encoding="utf-8")

required = [
    "MOEX_INDEX_DIAGNOSTIC_EXACT_COUNT",
    "SELECT ts AS latest",
    "ORDER BY ts DESC",
    "LIMIT 1",
    '"bars_status": bars_status',
    '"NOT_COUNTED_RUNTIME"',
    '"EXACT_DIAGNOSTIC"',
]

for item in required:
    if item not in text:
        raise SystemExit(f"ERROR=required_contract_missing:{item}")

legacy = (
    "SELECT max(ts) AS latest,count(*) AS bars "
    "FROM public.market_bars"
)

if legacy in text:
    raise SystemExit("ERROR=legacy_max_count_query_remains")

print("source_contract=OK")
PY

PLAN="$(
    psql -X -d finam_core -Atqc "
    EXPLAIN
    SELECT ts AS latest
    FROM public.market_bars
    WHERE symbol='SBER@MISX'
      AND timeframe='M1'
    ORDER BY ts DESC
    LIMIT 1;
    "
)"

printf '%s\n' "$PLAN"

grep -q "Limit" <<<"$PLAN" || {
    echo "ERROR=limit_plan_missing"
    exit 1
}

grep -Eq \
    "market_bars_pkey|idx_market_bars_symbol_tf_ts" \
    <<<"$PLAN" || {
        echo "ERROR=expected_market_bars_index_not_used"
        exit 1
    }

if grep -q "Seq Scan" <<<"$PLAN"; then
    echo "ERROR=sequential_scan_remains"
    exit 1
fi

DEFAULT_FLAG="$(
    PYTHONPATH=src python - <<'PY'
from scripts.run_moex_index_online_v2 import DIAGNOSTIC_EXACT_COUNT
print(int(DIAGNOSTIC_EXACT_COUNT))
PY
)"

[[ "$DEFAULT_FLAG" == "0" ]] || {
    echo "ERROR=exact_count_enabled_by_default"
    exit 1
}

ENABLED_FLAG="$(
    MOEX_INDEX_DIAGNOSTIC_EXACT_COUNT=1 \
    PYTHONPATH=src \
    python - <<'PY'
from scripts.run_moex_index_online_v2 import DIAGNOSTIC_EXACT_COUNT
print(int(DIAGNOSTIC_EXACT_COUNT))
PY
)"

[[ "$ENABLED_FLAG" == "1" ]] || {
    echo "ERROR=diagnostic_flag_not_working"
    exit 1
}

echo "default_exact_count=0"
echo "diagnostic_exact_count=available"
echo "VERDICT=TEST_MOEX_INDEX_ONLINE_FAST_STATE_V1_OK"
exit 0
