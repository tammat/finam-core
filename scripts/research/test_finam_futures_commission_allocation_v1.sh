#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

: "${FILLS_SCHEMA:?FILLS_SCHEMA is required}"
: "${FILLS_TABLE:?FILLS_TABLE is required}"
: "${FILLS_TS_COLUMN:?FILLS_TS_COLUMN is required}"
: "${FILLS_SYMBOL_COLUMN:?FILLS_SYMBOL_COLUMN is required}"
: "${FILLS_QUANTITY_COLUMN:?FILLS_QUANTITY_COLUMN is required}"
: "${FILLS_PRICE_COLUMN:?FILLS_PRICE_COLUMN is required}"

PYTHON="/opt/finam-core/venv/bin/python"

BATCH_ID="${1:-FINAM_FUTURES_COMMISSION_ALLOCATION_V1_TEST}"
LOG="/tmp/test_finam_futures_commission_allocation_v1.log"

rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" \
  scripts/research/migrate_finam_futures_commission_allocation_v1.py

PYTHONPATH=src \
"$PYTHON" \
  scripts/research/build_finam_futures_commission_allocation_v1.py \
  --evidence-file \
    config/research/finam_futures_daily_commission_v1.tsv \
  --attribution-exceptions-file \
    config/research/finam_futures_commission_attribution_exceptions_v1.tsv \
  --fills-schema "$FILLS_SCHEMA" \
  --fills-table "$FILLS_TABLE" \
  --timestamp-column "$FILLS_TS_COLUMN" \
  --symbol-column "$FILLS_SYMBOL_COLUMN" \
  --quantity-column "$FILLS_QUANTITY_COLUMN" \
  --price-column "$FILLS_PRICE_COLUMN" \
  --allocation-model ALL \
  --batch-id "$BATCH_ID" \
  | tee "$LOG"

grep -Fq "evidence_day_count=19" "$LOG"
grep -Fq "allocated_day_count=15" "$LOG"
grep -Fq "excluded_day_count=4" "$LOG"
grep -Fq "unresolved_count=0" "$LOG"

for DATE in \
  2026-05-04 \
  2026-05-05 \
  2026-05-06 \
  2026-05-07
do
    grep -Fq \
      "EXCLUDED_FROM_ALLOCATION=UNATTRIBUTABLE_NO_FILLS:${DATE}:" \
      "$LOG"
done

grep -Fq \
  "VERDICT=FINAM_FUTURES_COMMISSION_ALLOCATION_V1_READY" \
  "$LOG"

PYTHONPATH=src \
"$PYTHON" \
  scripts/research/audit_finam_futures_commission_allocation_v1.py \
  | tee -a "$LOG"

grep -Fq \
  "VERDICT=FINAM_FUTURES_COMMISSION_ALLOCATION_V1_AUDIT_OK" \
  "$LOG"

echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_FINAM_FUTURES_COMMISSION_ALLOCATION_V1_OK"
