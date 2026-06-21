#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_multi_asset_compression_expansion_history_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_multi_asset_compression_expansion_history_v1.py \
  --migrate --save | tee "$out"

grep -q "MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_V1_OK" "$out"
grep -q "VERDICT=MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_SAVED" "$out"
grep -q "snapshot_table_exists=1" "$out"
grep -q "row_table_exists=1" "$out"
grep -q "runtime_changes_required=0" "$out"
grep -q "execution_changes_required=0" "$out"
grep -q "real_trading_enabled=0" "$out"
grep -q "execution_enabled=0" "$out"

psql "$DATABASE_URL" -c "
select
  count(*) as snapshots,
  max(created_at) as last_snapshot
from analytics_multi_asset_compression_snapshot_v1;
"

psql "$DATABASE_URL" -c "
select
  status,
  count(*) as rows
from analytics_multi_asset_compression_row_v1
group by status
order by rows desc;
"

echo "VERDICT=MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_TEST_OK"
echo "TEST_MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_V1_OK"
