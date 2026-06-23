#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_TIMER_OBSERVATION_V1 ==="

echo "=== TIMER_STATUS ==="
systemctl list-timers --all | grep finam-rs-bottom-runtime-live-collector || true

echo "=== SERVICE_JOURNAL ==="
journalctl -u finam-rs-bottom-runtime-live-collector.service --since "20 minutes ago" --no-pager \
  | grep -E "RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_V1|COLLECTOR_ROW|VERDICT=RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_OK|ERROR|Traceback" \
  | tee /tmp/rs_bottom_runtime_live_collector_timer_observation_v1_journal.log || true

grep -q "VERDICT=RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_OK" \
  /tmp/rs_bottom_runtime_live_collector_timer_observation_v1_journal.log

echo "=== DASHBOARD_HOME_CHECK ==="
curl -fsS "http://127.0.0.1:8088/" \
  | tee /tmp/rs_bottom_runtime_live_collector_timer_observation_v1_home.html >/dev/null

grep -q "RS Bottom Runtime Dry Run V1" /tmp/rs_bottom_runtime_live_collector_timer_observation_v1_home.html
grep -q "Fresh rows 90m" /tmp/rs_bottom_runtime_live_collector_timer_observation_v1_home.html
grep -q "Last created" /tmp/rs_bottom_runtime_live_collector_timer_observation_v1_home.html
grep -q "GDU6@RTSX" /tmp/rs_bottom_runtime_live_collector_timer_observation_v1_home.html
grep -q "GLU6@RTSX" /tmp/rs_bottom_runtime_live_collector_timer_observation_v1_home.html
grep -q "NGM6@RTSX" /tmp/rs_bottom_runtime_live_collector_timer_observation_v1_home.html

echo "VERDICT=RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_TIMER_OBSERVATION_OK"
echo "TEST_RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_TIMER_OBSERVATION_V1_OK"
