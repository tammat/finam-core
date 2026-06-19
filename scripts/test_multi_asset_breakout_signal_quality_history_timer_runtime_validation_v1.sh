#!/usr/bin/env bash
set -euo pipefail

echo "=== MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_TIMER_RUNTIME_VALIDATION_V1 ==="

timer="finam-multi-asset-breakout-history.timer"
service="finam-multi-asset-breakout-history.service"

timer_enabled="$(systemctl is-enabled "$timer" 2>/dev/null || true)"
timer_active="$(systemctl is-active "$timer" 2>/dev/null || true)"
service_state="$(systemctl is-active "$service" 2>/dev/null || true)"

before_snapshot="$(psql "$DATABASE_URL" -Atc "select count(*) from analytics_multi_asset_breakout_snapshot_v1;")"
before_rows="$(psql "$DATABASE_URL" -Atc "select count(*) from analytics_multi_asset_breakout_row_v1;")"
before_last="$(psql "$DATABASE_URL" -Atc "select coalesce(max(created_at)::text,'') from analytics_multi_asset_breakout_snapshot_v1;")"

echo "timer_enabled=$timer_enabled"
echo "timer_active=$timer_active"
echo "service_state=$service_state"
echo "before_snapshot=$before_snapshot"
echo "before_rows=$before_rows"
echo "before_last=$before_last"

if [ "$timer_active" != "active" ]; then
  echo "VERDICT=HISTORY_TIMER_NOT_ACTIVE"
  exit 1
fi

echo "waiting_for_next_timer_run=330s"
sleep 330

after_snapshot="$(psql "$DATABASE_URL" -Atc "select count(*) from analytics_multi_asset_breakout_snapshot_v1;")"
after_rows="$(psql "$DATABASE_URL" -Atc "select count(*) from analytics_multi_asset_breakout_row_v1;")"
after_last="$(psql "$DATABASE_URL" -Atc "select coalesce(max(created_at)::text,'') from analytics_multi_asset_breakout_snapshot_v1;")"

echo "after_snapshot=$after_snapshot"
echo "after_rows=$after_rows"
echo "after_last=$after_last"

runtime_allow="$(psql "$DATABASE_URL" -Atc "select coalesce(current_setting('app.runtime_allow', true),'0');" 2>/dev/null || echo 0)"
execution_enabled="$(psql "$DATABASE_URL" -Atc "select coalesce(current_setting('app.execution_enabled', true),'0');" 2>/dev/null || echo 0)"

echo "runtime_allow=$runtime_allow"
echo "execution_enabled=$execution_enabled"

if [ "$after_snapshot" -le "$before_snapshot" ]; then
  echo "VERDICT=HISTORY_TIMER_NO_NEW_SNAPSHOT"
  exit 1
fi

if [ "$after_rows" -le "$before_rows" ]; then
  echo "VERDICT=HISTORY_TIMER_NO_NEW_ROWS"
  exit 1
fi

if [ "$after_last" = "$before_last" ]; then
  echo "VERDICT=HISTORY_TIMER_LAST_TIMESTAMP_NOT_CHANGED"
  exit 1
fi

echo "VERDICT=MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_TIMER_RUNTIME_VALIDATION_OK"
echo "TEST_MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_TIMER_RUNTIME_VALIDATION_V1_OK"
