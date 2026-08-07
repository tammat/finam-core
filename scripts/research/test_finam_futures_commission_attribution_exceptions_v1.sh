#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

FILE="config/research/finam_futures_commission_attribution_exceptions_v1.tsv"

[[ -s "$FILE" ]]

ROW_COUNT="$(tail -n +2 "$FILE" | wc -l)"
EXCEPTION_COUNT="$(grep -c $'\tUNATTRIBUTABLE_NO_FILLS\t' "$FILE")"

echo "exception_row_count=$ROW_COUNT"
echo "unattributable_no_fills_count=$EXCEPTION_COUNT"

[[ "$ROW_COUNT" -eq 4 ]]
[[ "$EXCEPTION_COUNT" -eq 4 ]]

for DATE in 2026-05-04 2026-05-05 2026-05-06 2026-05-07; do
    grep -Fq "$DATE" "$FILE"
    echo "EXCEPTION_CONFIRMED date=$DATE"
done

echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_FINAM_FUTURES_COMMISSION_ATTRIBUTION_EXCEPTIONS_V1_OK"
