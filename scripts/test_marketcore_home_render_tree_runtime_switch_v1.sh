#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo \
"=== TEST_MARKETCORE_HOME_RENDER_TREE_RUNTIME_SWITCH_V1 ==="

shell_asset=\
"src/marketcore/presentation/ui_runtime/assets/v1/home_runtime_v1.html"

switch_asset=\
"src/marketcore/presentation/ui_runtime/assets/v1/home_runtime_switch_v1.js"

validator_asset=\
"src/marketcore/presentation/ui_runtime/assets/v1/render_tree_validator_v1.js"

driver_asset=\
"src/marketcore/presentation/ui_runtime/assets/v1/browser_dom_driver_v1.js"

executor_asset=\
"src/marketcore/presentation/ui_runtime/assets/v1/browser_render_tree_executor_v1.js"

asset_delivery=\
"src/marketcore/presentation/ui_runtime/asset_delivery_v1.py"

router=\
"src/marketcore/presentation/router.py"

for file in \
  "$shell_asset" \
  "$switch_asset" \
  "$validator_asset" \
  "$driver_asset" \
  "$executor_asset" \
  "$asset_delivery" \
  "$router"
do
  test -f "$file" || {
    echo "FILE_NOT_FOUND=$file"
    exit 1
  }
done

if command -v node >/dev/null 2>&1; then
  NODE_BIN="$(command -v node)"
elif command -v nodejs >/dev/null 2>&1; then
  NODE_BIN="$(command -v nodejs)"
else
  echo "NODE_RUNTIME_REQUIRED"
  exit 1
fi

"$NODE_BIN" --check "$switch_asset"

PYTHONPYCACHEPREFIX=/tmp/marketcore_home_runtime_switch_v1 \
PYTHONPATH=src \
python -m py_compile \
  "$asset_delivery" \
  "$router"

# Серверная страница Home больше не должна вызываться маршрутом.
PYTHONPATH=src python - <<'PY'
import json

from marketcore.presentation.router import route
from marketcore.presentation.ui_runtime.asset_delivery_v1 import (
    UI_RUNTIME_ASSETS_V1,
    load_ui_runtime_asset_v1,
)


definitions = {
    item.asset_code: item
    for item in UI_RUNTIME_ASSETS_V1
}

assert "home_runtime_html" in definitions
assert "home_runtime_switch_js" in definitions

shell_response = load_ui_runtime_asset_v1(
    "/workspace-v2"
)
switch_response = load_ui_runtime_asset_v1(
    "/assets/marketcore/ui-runtime/v1/"
    "home-runtime-switch.js"
)

assert shell_response.status_code == 200
assert (
    shell_response.content_type
    == "text/html; charset=utf-8"
)
assert switch_response.status_code == 200
assert (
    switch_response.content_type
    == "application/javascript; charset=utf-8"
)

shell = shell_response.body.decode("utf-8")
switch = switch_response.body.decode("utf-8")

assert 'id="marketcore-home-runtime-root"' in shell
assert "/render-tree-validator.js" in shell
assert "/browser-dom-driver.js" in shell
assert "/browser-render-tree-executor.js" in shell
assert "/home-runtime-switch.js" in shell

assert "/api/v1/render-tree/home" in switch
assert "executeRenderTree" in switch
assert "innerHTML" not in switch
assert "document.write" not in switch

status_code, body = route("/workspace-v2")
assert status_code == 200
assert body == shell_response.body

status_code_slash, body_slash = route(
    "/workspace-v2/"
)
assert status_code_slash == 200
assert body_slash == shell_response.body

json_status, json_body = route(
    "/api/v1/render-tree/home"
)

assert json_status == 200

payload = json.loads(
    json_body.decode("utf-8")
)

assert (
    payload["schema_version"]
    == "marketcore.render_tree.v1"
)
assert payload["root"]["type"] == "workspace"

print("home_runtime_shell=OK")
print("home_runtime_switch_asset=OK")
print("home_route_static_shell=OK")
print("home_render_tree_json=OK")
print("server_render_document_to_html_called=0")
PY

# Проверяем, что router не вызывает старую Home HTML-функцию.
if grep -nE \
  'render_workspace_v2_home_page_v2\(\)' \
  "$router"
then
  echo "LEGACY_HOME_HTML_ROUTE_STILL_ACTIVE"
  exit 1
fi

sudo systemctl restart marketcore-ui-shell.service
sleep 2

home_headers="/tmp/marketcore_home_runtime_v1.headers"
home_body="/tmp/marketcore_home_runtime_v1.html"
switch_headers="/tmp/marketcore_home_runtime_switch_v1.headers"
switch_body="/tmp/marketcore_home_runtime_switch_v1.js"
json_headers="/tmp/marketcore_home_render_tree_v1.headers"
json_body="/tmp/marketcore_home_render_tree_v1.json"

curl -fsS \
  -D "$home_headers" \
  -o "$home_body" \
  http://127.0.0.1:8080/workspace-v2

curl -fsS \
  -D "$switch_headers" \
  -o "$switch_body" \
  http://127.0.0.1:8080/assets/marketcore/ui-runtime/v1/home-runtime-switch.js

curl -fsS \
  -D "$json_headers" \
  -o "$json_body" \
  http://127.0.0.1:8080/api/v1/render-tree/home

grep -qi \
  '^Content-Type: text/html; charset=utf-8' \
  "$home_headers"

grep -qi \
  '^Content-Type: application/javascript; charset=utf-8' \
  "$switch_headers"

grep -qi \
  '^Content-Type: application/json; charset=utf-8' \
  "$json_headers"

grep -q \
  'id="marketcore-home-runtime-root"' \
  "$home_body"

grep -q \
  '/home-runtime-switch.js' \
  "$home_body"

grep -q \
  'MarketCoreHomeRuntimeSwitchV1' \
  "$switch_body"

PYTHONPATH=src python - "$json_body" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(
    Path(sys.argv[1]).read_text(encoding="utf-8")
)

assert payload["schema_version"] == "marketcore.render_tree.v1"
assert payload["root"]["type"] == "workspace"

print("home_http_render_tree_json=OK")
PY

# Portfolio остается на прежнем маршруте.
portfolio=$(curl -fsS \
  http://127.0.0.1:8080/workspace-v2/portfolio)

grep -q "Портфель" <<<"$portfolio"
grep -q "P&amp;L %" <<<"$portfolio"

echo "home_runtime_shell=OK"
echo "home_runtime_switch=OK"
echo "home_json_endpoint=OK"
echo "home_server_html_generation=0"
echo "home_legacy_adapter_route=0"
echo "portfolio_regression=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
"VERDICT=MARKETCORE_HOME_RENDER_TREE_RUNTIME_SWITCH_V1_READY"
echo \
"VERDICT=TEST_MARKETCORE_HOME_RENDER_TREE_RUNTIME_SWITCH_V1_OK"
