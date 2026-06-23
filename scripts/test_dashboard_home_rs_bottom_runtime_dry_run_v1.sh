#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_DASHBOARD_HOME_RS_BOTTOM_RUNTIME_DRY_RUN_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

curl -fsS "http://127.0.0.1:8088/" \
  | tee /tmp/dashboard_home_rs_bottom_runtime_dry_run_v1.html >/dev/null

grep -q "RS Bottom Runtime Dry Run V1" /tmp/dashboard_home_rs_bottom_runtime_dry_run_v1.html
grep -q "Runtime decision" /tmp/dashboard_home_rs_bottom_runtime_dry_run_v1.html
grep -q "CONFIRMED" /tmp/dashboard_home_rs_bottom_runtime_dry_run_v1.html
grep -q "GDU6@RTSX" /tmp/dashboard_home_rs_bottom_runtime_dry_run_v1.html
grep -q "GLU6@RTSX" /tmp/dashboard_home_rs_bottom_runtime_dry_run_v1.html
grep -q "Fresh rows 90m" /tmp/dashboard_home_rs_bottom_runtime_dry_run_v1.html
grep -q "Реальная торговля" /tmp/dashboard_home_rs_bottom_runtime_dry_run_v1.html

echo "TEST_DASHBOARD_HOME_RS_BOTTOM_RUNTIME_DRY_RUN_V1_OK"
