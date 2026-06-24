#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_SESSION_GUARD_8088_STATUS_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

out=/tmp/gold_session_guard_8088_status_v1.html
curl -fsS http://127.0.0.1:8088/ | tee "$out" >/dev/null

grep -q "Gold session guard: shadow" "$out"
grep -q "Срабатываний пока нет" "$out"
grep -q "GDU6/GLU6 после 19:00 МСК" "$out"
grep -q "Audit за 24ч" "$out"

echo "VERDICT=GOLD_SESSION_GUARD_8088_STATUS_OK"
echo "TEST_GOLD_SESSION_GUARD_8088_STATUS_V1_OK"
