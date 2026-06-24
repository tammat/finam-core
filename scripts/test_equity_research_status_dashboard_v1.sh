#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_EQUITY_RESEARCH_STATUS_DASHBOARD_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

curl -fsS "http://127.0.0.1:8088/equities" \
  | tee /tmp/equity_research_status_dashboard_v1.html >/dev/null

grep -q "СТАТУС АКЦИЙ" /tmp/equity_research_status_dashboard_v1.html
grep -q "Research Only" /tmp/equity_research_status_dashboard_v1.html
grep -q "Виртуальные сделки" /tmp/equity_research_status_dashboard_v1.html
grep -q "Paper execution" /tmp/equity_research_status_dashboard_v1.html
grep -q "Runtime execution" /tmp/equity_research_status_dashboard_v1.html
grep -q "Акции не являются runtime-кандидатами" /tmp/equity_research_status_dashboard_v1.html

echo "TEST_EQUITY_RESEARCH_STATUS_DASHBOARD_V1_OK"
