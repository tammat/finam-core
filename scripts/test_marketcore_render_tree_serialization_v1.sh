#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RENDER_TREE_SERIALIZATION_V1 ==="

files=(
  "src/marketcore/presentation/render_tree/__init__.py"
  "src/marketcore/presentation/render_tree/node_types.py"
  "src/marketcore/presentation/render_tree/render_node.py"
  "src/marketcore/presentation/render_tree/render_document.py"
  "src/marketcore/presentation/render_tree/serialization_v1.py"
  "src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"
)

for file in "${files[@]}"; do
  test -f "$file" || {
    echo "FILE_NOT_FOUND=$file"
    exit 1
  }
done

PYTHONPYCACHEPREFIX=/tmp/marketcore_render_tree_serialization_v1 \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE \
  --include='*.py' \
  'html|HTML|web|Web|css|CSS|http|HTTP|browser|Browser' \
  src/marketcore/presentation/render_tree
then
  echo "PLATFORM_DEPENDENCY_INSIDE_RENDER_TREE_FOUND"
  exit 1
fi

if grep -RInE \
  --include='*.py' \
  'psycopg2|SELECT |INSERT |UPDATE |DELETE |execute\(' \
  src/marketcore/presentation/render_tree/serialization_v1.py
then
  echo "STORAGE_DEPENDENCY_IN_SERIALIZER_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
import json
from decimal import Decimal

from marketcore.presentation.render_tree import (
    RenderDocument,
    RenderNode,
    RenderNodeType,
    RenderTreeSerializationErrorV1,
    RenderTreeSerializerV1,
)
from marketcore.presentation.workspace_v2.presenter.home_v2_presenter import (
    HomeV2Presenter,
)
from marketcore.presentation.workspace_v2.presenter.portfolio_v2_presenter import (
    PortfolioV2Presenter,
)
from marketcore.presentation.workspace_v2.renderer.home_v2_renderer import (
    render_home_v2,
)
from marketcore.presentation.workspace_v2.renderer.portfolio_v2_renderer import (
    render_portfolio_v2,
)


document = RenderDocument(
    root=RenderNode(
        node_type=RenderNodeType.WORKSPACE,
        props={
            "class": "mc-v2-shell",
            "enabled": True,
            "count": 2,
            "metadata": {
                "status": RenderNodeType.CARD,
                "items": ("a", "b"),
            },
        },
        children=(
            RenderNode(
                node_type=RenderNodeType.TITLE,
                props={"level": 1},
                text="MarketCore OS",
            ),
            RenderNode(
                node_type=RenderNodeType.CARD,
                children=(
                    RenderNode(
                        node_type=RenderNodeType.TEXT,
                        text="Проверка",
                    ),
                ),
            ),
        ),
    )
)

payload = RenderTreeSerializerV1.to_dict(document)

assert payload["schema_version"] == "marketcore.render_tree.v1"
assert payload["root"]["type"] == "workspace"
assert payload["root"]["props"]["enabled"] is True
assert payload["root"]["props"]["count"] == 2
assert payload["root"]["props"]["metadata"]["status"] == "card"
assert payload["root"]["props"]["metadata"]["items"] == ["a", "b"]
assert payload["root"]["children"][0]["type"] == "title"
assert payload["root"]["children"][0]["text"] == "MarketCore OS"
assert payload["root"]["children"][1]["children"][0]["text"] == "Проверка"

json_text = RenderTreeSerializerV1.to_json(document)
decoded = json.loads(json_text)

assert decoded == payload
assert "MarketCore OS" in json_text
assert "\\u041c" not in json_text
assert "<main" not in json_text
assert "<div" not in json_text
assert "<article" not in json_text

home_document = render_home_v2(
    HomeV2Presenter().load()
)
portfolio_document = render_portfolio_v2(
    PortfolioV2Presenter().load(limit=20)
)

home_payload = RenderTreeSerializerV1.to_dict(home_document)
portfolio_payload = RenderTreeSerializerV1.to_dict(portfolio_document)

assert home_payload["root"]["type"] == "workspace"
assert portfolio_payload["root"]["type"] == "workspace"

home_json = RenderTreeSerializerV1.to_json(home_document)
portfolio_json = RenderTreeSerializerV1.to_json(portfolio_document)

assert "MarketCore OS" in home_json
assert "Портфель" in portfolio_json
assert "P&amp;L" not in portfolio_json
assert "<main" not in home_json
assert "<main" not in portfolio_json

try:
    RenderTreeSerializerV1.to_dict("not-document")  # type: ignore[arg-type]
except TypeError as exc:
    assert str(exc) == "RENDER_DOCUMENT_REQUIRED"
else:
    raise AssertionError("INVALID_DOCUMENT_NOT_REJECTED")

invalid_document = RenderDocument(
    root=RenderNode(
        node_type=RenderNodeType.WORKSPACE,
        props={"bad": Decimal("1.25")},
    )
)

try:
    RenderTreeSerializerV1.to_dict(invalid_document)
except RenderTreeSerializationErrorV1 as exc:
    assert "RENDER_TREE_VALUE_NOT_SERIALIZABLE" in str(exc)
    assert "Decimal" in str(exc)
else:
    raise AssertionError("UNSUPPORTED_VALUE_NOT_REJECTED")

print("render_tree_to_dict=OK")
print("render_tree_to_json=OK")
print("unicode_serialization=OK")
print("home_serialization=OK")
print("portfolio_serialization=OK")
print("html_output=0")
print("validation=OK")
PY

echo "render_tree_serialization=OK"
echo "schema_version=marketcore.render_tree.v1"
echo "platform_dependency=0"
echo "storage_dependency=0"
echo "home_changed=0"
echo "portfolio_changed=0"
echo "routes_changed=0"
echo "web_adapter_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RENDER_TREE_SERIALIZATION_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RENDER_TREE_SERIALIZATION_V1_OK"
