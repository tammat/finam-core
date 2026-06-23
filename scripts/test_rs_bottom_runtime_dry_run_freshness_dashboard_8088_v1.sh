#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_RUNTIME_DRY_RUN_FRESHNESS_DASHBOARD_8088_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

curl -fsS "http://127.0.0.1:8088/rs-bottom-runtime-dry-run" \
  | tee /tmp/rs_bottom_runtime_dry_run_freshness_dashboard_8088_v1.html >/dev/null

grep -q "RS Bottom Runtime Dry Run V1" /tmp/rs_bottom_runtime_dry_run_freshness_dashboard_8088_v1.html
grep -q "Freshness" /tmp/rs_bottom_runtime_dry_run_freshness_dashboard_8088_v1.html
grep -q "Fresh rows 90m" /tmp/rs_bottom_runtime_dry_run_freshness_dashboard_8088_v1.html
grep -q "Last signal" /tmp/rs_bottom_runtime_dry_run_freshness_dashboard_8088_v1.html
grep -q "Last created" /tmp/rs_bottom_runtime_dry_run_freshness_dashboard_8088_v1.html
grep -q "GDU6@RTSX" /tmp/rs_bottom_runtime_dry_run_freshness_dashboard_8088_v1.html
grep -q "GLU6@RTSX" /tmp/rs_bottom_runtime_dry_run_freshness_dashboard_8088_v1.html
grep -q "NGM6@RTSX" /tmp/rs_bottom_runtime_dry_run_freshness_dashboard_8088_v1.html

echo "TEST_RS_BOTTOM_RUNTIME_DRY_RUN_FRESHNESS_DASHBOARD_8088_V1_OK"
