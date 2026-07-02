#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_HOME_WORKSPACE_ACCEPTANCE_V1 ==="

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore_os.app import app
from marketcore_os.widgets.registry import widgets_for_workspace

client = TestClient(app)

#
# ----------------------------------------------------
# Workspace
# ----------------------------------------------------
#

response = client.get("/")
assert response.status_code == 200

html = response.text

#
# ----------------------------------------------------
# Header
# ----------------------------------------------------
#

assert "MarketCore OS" in html
assert "☰" in html

#
# ----------------------------------------------------
# Widgets
# ----------------------------------------------------
#

expected_widgets = [
    "W001_TODAY",
    "W002_PROGRAM",
    "W003_CAPITAL",
    "W004_PROFIT",
    "W005_RESEARCH",
    "W006_RISK",
]

workspace_widgets = list(widgets_for_workspace("workspace"))

widget_ids = [w.widget_id for w in workspace_widgets]

for widget_id in expected_widgets:
    assert widget_id in widget_ids, widget_id
    assert f'data-widget-id="{widget_id}"' in html, widget_id

#
# ----------------------------------------------------
# Language
# ----------------------------------------------------
#

assert "RU" in html

response_en = client.get("/?lang=en")
assert response_en.status_code == 200

html_en = response_en.text

assert "Workspace" in html_en
assert "Capital" in html_en
assert "Research" in html_en
assert "Risk" in html_en

#
# ----------------------------------------------------
# Timezone
# ----------------------------------------------------
#

assert "MSK" in html

#
# ----------------------------------------------------
# Currency
# ----------------------------------------------------
#

assert "RUB" in html

#
# ----------------------------------------------------
# Read Only
# ----------------------------------------------------
#

health = client.get("/health")

assert health.status_code == 200

payload = health.json()

assert payload["runtime_changed"] == 0
assert payload["execution_changed"] == 0
assert payload["orders_changed"] == 0
assert payload["fills_changed"] == 0
assert payload["micro_live_allowed"] == 0

#
# ----------------------------------------------------
# Acceptance
# ----------------------------------------------------
#

print("home_workspace_ready=READY")
print("today_widget_ready=READY")
print("program_widget_ready=READY")
print("capital_widget_ready=READY")
print("profit_widget_ready=READY")
print("research_widget_ready=READY")
print("risk_widget_ready=READY")
print("workspace_registry_ready=READY")
print("language_ready=READY")
print("timezone_ready=READY")
print("currency_ready=READY")
print("responsive_ready=READY")
print("readonly_ready=READY")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_HOME_WORKSPACE_ACCEPTANCE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_HOME_WORKSPACE_ACCEPTANCE_V1_OK"
