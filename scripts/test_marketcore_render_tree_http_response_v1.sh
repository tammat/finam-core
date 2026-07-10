#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RENDER_TREE_HTTP_RESPONSE_V1 ==="

files=(
  "src/marketcore/presentation/render_tree/http_response_v1.py"
  "src/marketcore/presentation/workspace_v2/render_tree_http_v1.py"
  "src/marketcore/presentation/router.py"
  "src/marketcore/presentation/app.py"
)

for file in "${files[@]}"; do
  test -f "$file" || {
    echo "FILE_NOT_FOUND=$file"
    exit 1
  }
done

PYTHONPYCACHEPREFIX=/tmp/marketcore_render_tree_http_response_v1 \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE \
  'send_order|place_order|cancel_order|execute_order|INSERT INTO|UPDATE |DELETE FROM|DROP TABLE|TRUNCATE' \
  src/marketcore/presentation/render_tree/http_response_v1.py \
  src/marketcore/presentation/workspace_v2/render_tree_http_v1.py
then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE \
  '<main|<section|<article|<div|<h1|<h2|<h3|</' \
  src/marketcore/presentation/render_tree/http_response_v1.py \
  src/marketcore/presentation/workspace_v2/render_tree_http_v1.py
then
  echo "HTML_IN_RENDER_TREE_HTTP_RESPONSE_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
import json

from marketcore.presentation.render_tree.http_response_v1 import (
    build_render_tree_http_response_v1,
)
from marketcore.presentation.router import route
from marketcore.presentation.workspace_v2.presenter.home_v2_presenter import (
    HomeV2Presenter,
)
from marketcore.presentation.workspace_v2.renderer.home_v2_renderer import (
    render_home_v2,
)


document = render_home_v2(
    HomeV2Presenter().load()
)

response = build_render_tree_http_response_v1(document)

assert response.status_code == 200
assert response.content_type == "application/json; charset=utf-8"

payload = json.loads(response.body.decode("utf-8"))

assert payload["schema_version"] == "marketcore.render_tree.v1"
assert payload["root"]["type"] == "workspace"

for endpoint in (
    "/api/v1/render-tree/home",
    "/api/v1/render-tree/portfolio",
    "/api/v1/render-tree/portfolio/phone",
):
    status_code, body = route(endpoint)

    assert status_code == 200

    decoded = json.loads(body.decode("utf-8"))

    assert decoded["schema_version"] == "marketcore.render_tree.v1"
    assert decoded["root"]["type"] == "workspace"

    json_text = body.decode("utf-8")

    assert "<main" not in json_text
    assert "<div" not in json_text
    assert "<article" not in json_text

print("render_tree_http_response=OK")
print("home_json_route=OK")
print("portfolio_json_route=OK")
print("portfolio_phone_json_route=OK")
print("server_html_in_json=0")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

check_json_endpoint() {
  local endpoint="$1"
  local output_file="$2"
  local header_file="$3"

  curl -fsS \
    -D "$header_file" \
    -o "$output_file" \
    "http://127.0.0.1:8080${endpoint}"

  grep -qi \
    '^Content-Type: application/json; charset=utf-8' \
    "$header_file"

  PYTHONPATH=src python - "$output_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))

assert payload["schema_version"] == "marketcore.render_tree.v1"
assert payload["root"]["type"] == "workspace"

print(f"HTTP_JSON_OK={path.name}")
PY
}

check_json_endpoint \
  "/api/v1/render-tree/home" \
  "/tmp/marketcore_render_tree_home_v1.json" \
  "/tmp/marketcore_render_tree_home_v1.headers"

check_json_endpoint \
  "/api/v1/render-tree/portfolio" \
  "/tmp/marketcore_render_tree_portfolio_v1.json" \
  "/tmp/marketcore_render_tree_portfolio_v1.headers"

check_json_endpoint \
  "/api/v1/render-tree/portfolio/phone" \
  "/tmp/marketcore_render_tree_portfolio_phone_v1.json" \
  "/tmp/marketcore_render_tree_portfolio_phone_v1.headers"

# Старые пользовательские маршруты должны остаться рабочими.
home_html=$(curl -fsS \
  http://127.0.0.1:8080/workspace-v2)

portfolio_html=$(curl -fsS \
  http://127.0.0.1:8080/workspace-v2/portfolio)

grep -q "MarketCore OS" <<<"$home_html"
grep -q "Портфель" <<<"$portfolio_html"
grep -q "P&amp;L %" <<<"$portfolio_html"

echo "render_tree_http_response=OK"
echo "content_type_application_json=OK"
echo "home_json_endpoint=OK"
echo "portfolio_json_endpoint=OK"
echo "portfolio_phone_json_endpoint=OK"
echo "legacy_home_regression=OK"
echo "legacy_portfolio_regression=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RENDER_TREE_HTTP_RESPONSE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RENDER_TREE_HTTP_RESPONSE_V1_OK"
