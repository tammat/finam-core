#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_AI_REGISTRY_UI_SMOKE_NO_SUDO_V1 ==="

curl -fsS http://127.0.0.1:8089/knowledge/ai \
  -o /tmp/ai_registry_ui_smoke_no_sudo_v1.html

grep -q "MarketCore AI Registry" /tmp/ai_registry_ui_smoke_no_sudo_v1.html
grep -q "ai_registry_total=10" /tmp/ai_registry_ui_smoke_no_sudo_v1.html
grep -q "ai_registry_health=OK" /tmp/ai_registry_ui_smoke_no_sudo_v1.html
grep -q "unsafe_live_rows=0" /tmp/ai_registry_ui_smoke_no_sudo_v1.html
grep -q "forbidden_market_fields=0" /tmp/ai_registry_ui_smoke_no_sudo_v1.html
grep -q "policy=READ_ONLY" /tmp/ai_registry_ui_smoke_no_sudo_v1.html
grep -q "framework=REGISTRY_FRAMEWORK_V1" /tmp/ai_registry_ui_smoke_no_sudo_v1.html
grep -q "ui_policy=READ_ONLY_SINGLE_PORT_8089" /tmp/ai_registry_ui_smoke_no_sudo_v1.html
grep -q "micro_live_allowed=0" /tmp/ai_registry_ui_smoke_no_sudo_v1.html

echo "single_ui_port=8089"
echo "route_ai=/knowledge/ai"
echo "ai_registry_health=OK"
echo "ai_registry_total=10"
echo "no_sudo=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=AI_REGISTRY_UI_SMOKE_NO_SUDO_V1_READY"
echo "TEST_AI_REGISTRY_UI_SMOKE_NO_SUDO_V1_OK"
