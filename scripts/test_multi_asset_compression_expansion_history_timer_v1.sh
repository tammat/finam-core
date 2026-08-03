#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_TIMER_V1 ==="

systemctl is-enabled finam-multi-asset-compression-history.timer
systemctl is-active finam-multi-asset-compression-history.timer

systemctl cat finam-multi-asset-compression-history.service | grep -q "build_multi_asset_compression_expansion_history_v1.py --migrate --save"
systemctl cat finam-multi-asset-compression-history.service | grep -q "EXECUTION_ENABLED=0"
systemctl cat finam-multi-asset-compression-history.service | grep -q "REAL_TRADING_ENABLED=0"

systemctl cat finam-multi-asset-compression-history.timer | grep -q "OnCalendar=\*-\*-\* 01:10:00 Europe/Moscow"

psql "$DATABASE_URL" -c "
select
  count(*) as snapshots,
  max(created_at) as last_snapshot
from analytics_multi_asset_compression_snapshot_v1;
"

psql "$DATABASE_URL" -c "
select
  count(*) as rows,
  max(created_at) as last_row
from analytics_multi_asset_compression_row_v1;
"

echo "VERDICT=MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_TIMER_READY"
echo "TEST_MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_TIMER_V1_OK"
