#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE SOURCE CLASSIFICATION BACKFILL APPLY V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_trade_source_classification_backfill_apply_v1.py

echo
echo "=== DRY MODE CHECK ==="
PYTHONPATH=src python3 src/scripts/research/build_trade_source_classification_backfill_apply_v1.py \
  | tee /tmp/trade_source_classification_backfill_apply_v1_dry.log

grep -q "TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_V1_OK" /tmp/trade_source_classification_backfill_apply_v1_dry.log
grep -q "db_update=0" /tmp/trade_source_classification_backfill_apply_v1_dry.log
grep -q "VERDICT=TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_MODE" /tmp/trade_source_classification_backfill_apply_v1_dry.log

echo
echo "=== APPLY MODE CHECK ==="
APPLY_TRADE_SOURCE_CLASSIFICATION=1 \
PYTHONPATH=src python3 src/scripts/research/build_trade_source_classification_backfill_apply_v1.py \
  | tee /tmp/trade_source_classification_backfill_apply_v1_apply.log

grep -q "TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_V1_OK" /tmp/trade_source_classification_backfill_apply_v1_apply.log
grep -q "db_update=1" /tmp/trade_source_classification_backfill_apply_v1_apply.log
grep -q "updated_rows=8323" /tmp/trade_source_classification_backfill_apply_v1_apply.log
grep -q "VERDICT=TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_OK" /tmp/trade_source_classification_backfill_apply_v1_apply.log

echo
echo "=== VERIFY DB CLASSIFICATION ==="
python3 - <<'PY'
import os
import psycopg2

dsn = os.environ["DATABASE_URL"]

sql = """
select
  payload->>'trade_source_class' as trade_source_class,
  count(*) as rows
from trades
where created_at >= now() - interval '30 days'
  and coalesce(is_invalid, false) = false
group by 1
order by rows desc;
"""

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

for cls, count in rows:
    print(f"VERIFY_TRADE_SOURCE_CLASS_ROW class={cls} rows={count}")

expected = {
    "HISTORICAL_REPLAY": 3752,
    "LEGACY_NG_SYNTHETIC_BACKFILL": 3326,
    "RUNTIME_OR_PAPER_CLEAN_ENOUGH": 688,
    "NORMALIZED_BUT_NOT_CLEAN_EDGE": 234,
    "NO_PAYLOAD_REVIEW": 180,
    "PAPER_FILL_FALLBACK": 113,
    "CONTEXT_GAP_REVIEW": 22,
    "REVIEW_REQUIRED": 8,
}

actual = {cls: count for cls, count in rows}

for cls, count in expected.items():
    if actual.get(cls) != count:
        raise SystemExit(f"VERIFY_FAILED class={cls} expected={count} actual={actual.get(cls)}")

print("VERIFY_TRADE_SOURCE_CLASSIFICATION_OK")
PY

echo TEST_TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_V1_OK
