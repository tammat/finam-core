#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_RUNTIME_PERFORMANCE_DASHBOARD_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

curl -fsS "http://127.0.0.1:8088/" \
  | tee /tmp/rs_bottom_runtime_performance_dashboard_v1.html >/dev/null

grep -q "EDGE HEALTH" /tmp/rs_bottom_runtime_performance_dashboard_v1.html
grep -q "Performance summary" /tmp/rs_bottom_runtime_performance_dashboard_v1.html
grep -q "Collector" /tmp/rs_bottom_runtime_performance_dashboard_v1.html
grep -q "Freshness" /tmp/rs_bottom_runtime_performance_dashboard_v1.html
grep -q "Risk mode" /tmp/rs_bottom_runtime_performance_dashboard_v1.html
grep -q "GDU6@RTSX" /tmp/rs_bottom_runtime_performance_dashboard_v1.html
grep -q "GLU6@RTSX" /tmp/rs_bottom_runtime_performance_dashboard_v1.html
grep -q "NGM6@RTSX" /tmp/rs_bottom_runtime_performance_dashboard_v1.html

echo "TEST_RS_BOTTOM_RUNTIME_PERFORMANCE_DASHBOARD_V1_OK"
