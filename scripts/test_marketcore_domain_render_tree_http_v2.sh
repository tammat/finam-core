#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

files=(
  src/marketcore/presentation/render_tree/v2/http_response.py
  src/marketcore/presentation/workspace_v2/render_tree_http_v2.py
  src/marketcore/presentation/router.py
  src/marketcore/presentation/app.py
)

for file in "${files[@]}"; do
  test -f "$file"
done

PYTHONPYCACHEPREFIX=/tmp/marketcore_domain_render_tree_http_v2 \
PYTHONPATH=src \
python3 -m py_compile "${files[@]}"

if grep -RInE \
  'send_order|place_order|cancel_order|execute_order|INSERT INTO|UPDATE |DELETE FROM|DROP TABLE|TRUNCATE' \
  src/marketcore/presentation/render_tree/v2/http_response.py \
  src/marketcore/presentation/workspace_v2/render_tree_http_v2.py
then
  echo "DOMAIN_RENDER_TREE_V2_HTTP_DANGEROUS_CODE_FOUND"
  exit 1
fi

PYTHONPATH=src .venv/bin/python - <<'PY'
import json

from marketcore.presentation.render_tree.v2.http_response import (
    RENDER_TREE_V2_MEDIA_TYPE,
    build_render_tree_http_response_v2,
)
from marketcore.presentation.router import route
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import (
    build_domain_document_v2,
)


response = build_render_tree_http_response_v2(build_domain_document_v2("HOME"))
assert response.status_code == 200
assert response.content_type == RENDER_TREE_V2_MEDIA_TYPE

endpoints = {
    "/api/v2/domain-render-tree/home": "operator.home.v2",
    "/api/v2/domain-render-tree/portfolio": "operator.portfolio.v2",
    "/api/v2/domain-render-tree/control-center": "operator.control_center.v2",
}

for endpoint, document_id in endpoints.items():
    status_code, body = route(endpoint, {"timezone": ["Europe/Moscow"]})
    assert status_code == 200
    payload = json.loads(body)
    assert payload["schema_version"] == "marketcore.render_tree.v2"
    assert payload["document_id"] == document_id
    assert payload["timezone_code"] == "Europe/Moscow"
    encoded = body.decode("utf-8")
    assert '"class"' not in encoded
    assert '"style"' not in encoded
    assert '"href"' not in encoded

status_code, body = route(
    "/api/v2/domain-render-tree/home",
    {"timezone": ["UTC"]},
)
assert status_code == 200
assert json.loads(body)["timezone_code"] == "UTC"

print("vendor_json_media_type=OK")
print("domain_render_tree_routes=3")
print("timezone_query=OK")
print("platform_semantics=0")
PY

echo "runtime_actions_changed=0"
echo "service_restart=0"
echo "VERDICT=TEST_MARKETCORE_DOMAIN_RENDER_TREE_HTTP_V2_OK"
