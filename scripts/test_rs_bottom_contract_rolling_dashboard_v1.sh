#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_CONTRACT_ROLLING_DASHBOARD_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

curl -fsS "http://127.0.0.1:8088/rs-bottom-contract-rolling" \
  | tee /tmp/rs_bottom_contract_rolling_dashboard_v1.html >/dev/null

grep -q "RS Bottom: rolling-аудит контрактов" /tmp/rs_bottom_contract_rolling_dashboard_v1.html
grep -q "BOTTOM3 + COMPRESSION_RANGE" /tmp/rs_bottom_contract_rolling_dashboard_v1.html
grep -q "PRIMARY" /tmp/rs_bottom_contract_rolling_dashboard_v1.html
grep -q "REJECT" /tmp/rs_bottom_contract_rolling_dashboard_v1.html

echo "TEST_RS_BOTTOM_CONTRACT_ROLLING_DASHBOARD_V1_OK"
