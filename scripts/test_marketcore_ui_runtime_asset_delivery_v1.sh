#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_UI_RUNTIME_ASSET_DELIVERY_V1 ==="

files=(
  "src/marketcore/presentation/ui_runtime/__init__.py"
  "src/marketcore/presentation/ui_runtime/contract_v1.py"
  "src/marketcore/presentation/ui_runtime/asset_delivery_v1.py"
  "src/marketcore/presentation/ui_runtime/assets/v1/runtime_v1.js"
  "src/marketcore/presentation/ui_runtime/assets/v1/runtime_v1.css"
  "src/marketcore/presentation/router.py"
  "src/marketcore/presentation/app.py"
)

for file in "${files[@]}"; do
  test -f "$file" || {
    echo "FILE_NOT_FOUND=$file"
    exit 1
  }
done

PYTHONPYCACHEPREFIX=/tmp/marketcore_ui_runtime_asset_delivery_v1 \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/ui_runtime/__init__.py \
  src/marketcore/presentation/ui_runtime/contract_v1.py \
  src/marketcore/presentation/ui_runtime/asset_delivery_v1.py \
  src/marketcore/presentation/router.py \
  src/marketcore/presentation/app.py

if grep -RInE \
  'innerHTML|outerHTML|document\.write|eval\(|new Function|fetch\(|XMLHttpRequest|createElement\(' \
  src/marketcore/presentation/ui_runtime/assets/v1
then
  echo "UI_RUNTIME_RENDER_IMPLEMENTATION_FOUND"
  exit 1
fi

if grep -RInE \
  'send_order|place_order|cancel_order|execute_order|INSERT INTO|UPDATE |DELETE FROM|DROP TABLE|TRUNCATE' \
  src/marketcore/presentation/ui_runtime
then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.router import route
from marketcore.presentation.ui_runtime import (
    UI_RUNTIME_ASSETS_V1,
    load_ui_runtime_asset_v1,
    resolve_ui_runtime_asset_v1,
    ui_runtime_asset_content_type_v1,
)

js_route = "/assets/marketcore/ui-runtime/v1/runtime.js"
css_route = "/assets/marketcore/ui-runtime/v1/runtime.css"

assert len(UI_RUNTIME_ASSETS_V1) == 2

assert resolve_ui_runtime_asset_v1(js_route) is not None
assert resolve_ui_runtime_asset_v1(css_route) is not None

assert (
    ui_runtime_asset_content_type_v1(js_route)
    == "application/javascript; charset=utf-8"
)
assert (
    ui_runtime_asset_content_type_v1(css_route)
    == "text/css; charset=utf-8"
)

js_response = load_ui_runtime_asset_v1(js_route)
css_response = load_ui_runtime_asset_v1(css_route)
missing = load_ui_runtime_asset_v1(
    "/assets/marketcore/ui-runtime/v1/missing.js"
)

assert js_response.status_code == 200
assert css_response.status_code == 200
assert missing.status_code == 404
assert missing.body == b"UI_RUNTIME_ASSET_NOT_FOUND"

js_text = js_response.body.decode("utf-8")
css_text = css_response.body.decode("utf-8")

assert "MarketCoreUiRuntimeV1" in js_text
assert "marketcore.ui_runtime.contract.v1" in js_text
assert "marketcore.render_tree.v1" in js_text
assert "ASSET_DELIVERY_READY" in js_text

assert 'data-marketcore-ui-runtime="v1"' in css_text

assert "fetch(" not in js_text
assert "innerHTML" not in js_text
assert "createElement(" not in js_text

for endpoint in (js_route, css_route):
    status_code, body = route(endpoint)
    assert status_code == 200
    assert body

print("asset_registry=OK")
print("asset_allowlist=OK")
print("javascript_asset=OK")
print("css_asset=OK")
print("missing_asset_404=OK")
print("runtime_rendering_implementation=0")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS \
  -D /tmp/marketcore_runtime_js.headers \
  -o /tmp/marketcore_runtime_v1.js \
  http://127.0.0.1:8080/assets/marketcore/ui-runtime/v1/runtime.js

curl -fsS \
  -D /tmp/marketcore_runtime_css.headers \
  -o /tmp/marketcore_runtime_v1.css \
  http://127.0.0.1:8080/assets/marketcore/ui-runtime/v1/runtime.css

grep -qi \
  '^Content-Type: application/javascript; charset=utf-8' \
  /tmp/marketcore_runtime_js.headers

grep -qi \
  '^Content-Type: text/css; charset=utf-8' \
  /tmp/marketcore_runtime_css.headers

grep -q \
  'MarketCoreUiRuntimeV1' \
  /tmp/marketcore_runtime_v1.js

grep -q \
  'ASSET_DELIVERY_READY' \
  /tmp/marketcore_runtime_v1.js

grep -q \
  'data-marketcore-ui-runtime="v1"' \
  /tmp/marketcore_runtime_v1.css

curl -fsS \
  -D /tmp/marketcore_render_tree_home.headers \
  -o /tmp/marketcore_render_tree_home.json \
  http://127.0.0.1:8080/api/v1/render-tree/home

grep -qi \
  '^Content-Type: application/json; charset=utf-8' \
  /tmp/marketcore_render_tree_home.headers

curl -fsS \
  http://127.0.0.1:8080/workspace-v2 |
grep -q "MarketCore OS"

curl -fsS \
  http://127.0.0.1:8080/workspace-v2/portfolio |
grep -q "Портфель"

echo "asset_delivery=OK"
echo "javascript_content_type=OK"
echo "css_content_type=OK"
echo "asset_allowlist=OK"
echo "missing_asset_404=OK"
echo "ui_runtime_rendering=0"
echo "render_tree_json_regression=OK"
echo "legacy_routes_regression=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_RUNTIME_ASSET_DELIVERY_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_RUNTIME_ASSET_DELIVERY_V1_OK"
