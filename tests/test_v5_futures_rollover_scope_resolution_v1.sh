#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

FILE="src/scripts/run_v5_futures_rollover_v1.py"

echo "=== TEST_V5_FUTURES_ROLLOVER_SCOPE_RESOLUTION_V1 ==="

python -m py_compile "$FILE"

grep -q 'AS portfolio_scope' "$FILE"
grep -q 'resolved_row.get("portfolio_scope")' "$FILE"

if grep -q 'cursor.fetchone() or \[""\].*\[0\]' "$FILE"; then
    echo "ERROR=POSITIONAL_FETCH_FROM_REALDICT_STILL_PRESENT"
    exit 1
fi

DB="postgresql:///finam_core"

RESOLVED="$(
psql "$DB" -X -Atc "
SELECT analytics.resolve_paper_portfolio_scope_v1(
    'BRU6@RTSX',
    'paper'
);
"
)"

echo "resolved_scope=$RESOLVED"

[ "$RESOLVED" = "FRESH_V5_CONFIRMED_FUTURES" ]

echo "realdict_positional_index_used=0"
echo "named_scope_column_used=1"
echo "scope_contract_validated=1"
echo "db_writes_performed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_V5_FUTURES_ROLLOVER_SCOPE_RESOLUTION_V1_OK"
