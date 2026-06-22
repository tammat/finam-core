#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_ROUTE_RENDER_RESTORE_V1 ==="

for route in /summary /compression-history /journal; do
  html="$(curl -fsS "http://127.0.0.1:8088${route}")"

  if echo "$html" | grep -q "Нет подготовленного представления"; then
    echo "UNPREPARED_PAGE route=${route}"
    exit 1
  fi

  if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
    echo "DIRTY_OUTPUT route=${route}"
    exit 1
  fi

  echo "PAGE_OK route=${route}"
done

echo "VERDICT=DASHBOARD_ROUTE_RENDER_RESTORE_OK"
echo "TEST_DASHBOARD_ROUTE_RENDER_RESTORE_V1_OK"
