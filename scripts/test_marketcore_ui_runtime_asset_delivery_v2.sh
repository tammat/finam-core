#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core

files=(
  src/marketcore/presentation/ui_runtime/asset_delivery_v2.py
  src/marketcore/presentation/ui_runtime/assets/v2/render_tree_validator_v2.js
  src/marketcore/presentation/ui_runtime/assets/v2/domain_render_tree_runtime_v2.js
  src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js
  src/marketcore/presentation/ui_runtime/assets/v2/browser_bootstrap_v2.js
  src/marketcore/presentation/ui_runtime/assets/v2/browser_presentation_services_v2.js
  src/marketcore/presentation/router.py
  src/marketcore/presentation/app.py
)
for file in "${files[@]}"; do test -f "$file"; done
PYTHONPATH=src .venv/bin/python -m py_compile src/marketcore/presentation/ui_runtime/asset_delivery_v2.py src/marketcore/presentation/router.py src/marketcore/presentation/app.py
for file in src/marketcore/presentation/ui_runtime/assets/v2/*.js; do node --check "$file"; done

PYTHONPATH=src .venv/bin/python - <<'PY'
from marketcore.presentation.router import route
from marketcore.presentation.ui_runtime.asset_delivery_v2 import UI_RUNTIME_ASSETS_V2, load_ui_runtime_asset_v2

assert len(UI_RUNTIME_ASSETS_V2) == 5
for asset in UI_RUNTIME_ASSETS_V2:
    response = load_ui_runtime_asset_v2(asset.route)
    assert response.status_code == 200
    assert response.content_type == "application/javascript; charset=utf-8"
    status, body = route(asset.route)
    assert status == 200 and body == response.body
assert load_ui_runtime_asset_v2("/assets/marketcore/ui-runtime/v2/missing.js").status_code == 404
print("asset_allowlist=5")
PY

for asset in render-tree-validator domain-render-tree-runtime browser-platform-driver browser-bootstrap browser-presentation-services; do
  curl -fsS -D /tmp/mc-v2-$asset.headers -o /tmp/mc-v2-$asset.js "http://127.0.0.1:8080/assets/marketcore/ui-runtime/v2/$asset.js"
  grep -qi '^Content-Type: application/javascript; charset=utf-8' /tmp/mc-v2-$asset.headers
done

if find src/marketcore/presentation/ui_runtime/assets/v2 -type f \( -name '*.html' -o -name '*.css' \) | grep .; then
  echo V2_HTML_CSS_ASSET_FORBIDDEN
  exit 1
fi

echo html_assets=0
echo css_assets=0
echo MARKETCORE_UI_RUNTIME_ASSET_DELIVERY_V2_OK
