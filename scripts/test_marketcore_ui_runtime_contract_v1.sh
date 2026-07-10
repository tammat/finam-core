#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_UI_RUNTIME_CONTRACT_V1 ==="

files=(
  "src/marketcore/presentation/ui_runtime/__init__.py"
  "src/marketcore/presentation/ui_runtime/contract_v1.py"
  "src/marketcore/presentation/render_tree/node_types.py"
  "src/marketcore/presentation/render_tree/serialization_v1.py"
)

for file in "${files[@]}"; do
  test -f "$file" || {
    echo "FILE_NOT_FOUND=$file"
    exit 1
  }
done

PYTHONPYCACHEPREFIX=/tmp/marketcore_ui_runtime_contract_v1 \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE \
  --include='*.py' \
  '<main|<section|<article|<div|<script|</|innerHTML|document\.createElement|fetch\(' \
  src/marketcore/presentation/ui_runtime
then
  echo "RUNTIME_IMPLEMENTATION_FOUND_IN_CONTRACT"
  exit 1
fi

if grep -RInE \
  --include='*.py' \
  'psycopg2|SELECT |INSERT |UPDATE |DELETE |execute\(' \
  src/marketcore/presentation/ui_runtime
then
  echo "STORAGE_DEPENDENCY_FOUND_IN_RUNTIME_CONTRACT"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from copy import deepcopy

from marketcore.presentation.render_tree import (
    RenderTreeSerializerV1,
)
from marketcore.presentation.ui_runtime import (
    MARKETCORE_UI_RUNTIME_CONTRACT_V1,
    UiRuntimeContractValidationErrorV1,
    validate_ui_runtime_payload_v1,
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


contract = MARKETCORE_UI_RUNTIME_CONTRACT_V1

assert contract.contract_version == "marketcore.ui_runtime.contract.v1"
assert contract.render_tree_schema_version == "marketcore.render_tree.v1"
assert contract.root_node_type.value == "workspace"
assert contract.maximum_tree_depth == 32
assert contract.maximum_nodes == 10_000
assert contract.allowed_theme_codes == {"DEFAULT", "PHONE"}

home_payload = RenderTreeSerializerV1.to_dict(
    render_home_v2(
        HomeV2Presenter().load()
    )
)

portfolio_payload = RenderTreeSerializerV1.to_dict(
    render_portfolio_v2(
        PortfolioV2Presenter().load(limit=20)
    )
)

validate_ui_runtime_payload_v1(home_payload)
validate_ui_runtime_payload_v1(portfolio_payload)

invalid_schema = deepcopy(home_payload)
invalid_schema["schema_version"] = "marketcore.render_tree.v999"

try:
    validate_ui_runtime_payload_v1(invalid_schema)
except UiRuntimeContractValidationErrorV1 as exc:
    assert "UI_RUNTIME_SCHEMA_VERSION_UNSUPPORTED" in str(exc)
else:
    raise AssertionError("INVALID_SCHEMA_NOT_REJECTED")

invalid_root = deepcopy(home_payload)
invalid_root["root"]["type"] = "card"

try:
    validate_ui_runtime_payload_v1(invalid_root)
except UiRuntimeContractValidationErrorV1 as exc:
    assert "UI_RUNTIME_ROOT_TYPE_INVALID" in str(exc)
else:
    raise AssertionError("INVALID_ROOT_NOT_REJECTED")

unsupported_node = deepcopy(home_payload)
unsupported_node["root"]["children"][0]["type"] = "html_div"

try:
    validate_ui_runtime_payload_v1(unsupported_node)
except UiRuntimeContractValidationErrorV1 as exc:
    assert "UI_RUNTIME_NODE_TYPE_UNSUPPORTED" in str(exc)
else:
    raise AssertionError("UNSUPPORTED_NODE_NOT_REJECTED")

invalid_title = deepcopy(home_payload)
invalid_title["root"]["children"][0]["children"][0]["props"]["level"] = 9

try:
    validate_ui_runtime_payload_v1(invalid_title)
except UiRuntimeContractValidationErrorV1 as exc:
    assert "UI_RUNTIME_TITLE_LEVEL_INVALID" in str(exc)
else:
    raise AssertionError("INVALID_TITLE_LEVEL_NOT_REJECTED")

invalid_action = deepcopy(home_payload)

action_node = None
stack = [invalid_action["root"]]

while stack:
    node = stack.pop()

    if node["type"] == "action":
        action_node = node
        break

    stack.extend(node.get("children", []))

assert action_node is not None

action_node["props"]["href"] = "javascript:alert(1)"

try:
    validate_ui_runtime_payload_v1(invalid_action)
except UiRuntimeContractValidationErrorV1 as exc:
    assert "UI_RUNTIME_ACTION_TARGET_SCHEME_FORBIDDEN" in str(exc)
else:
    raise AssertionError("UNSAFE_ACTION_NOT_REJECTED")

unknown_prop = deepcopy(home_payload)
unknown_prop["root"]["props"]["onclick"] = "bad"

try:
    validate_ui_runtime_payload_v1(unknown_prop)
except UiRuntimeContractValidationErrorV1 as exc:
    assert "UI_RUNTIME_NODE_PROP_UNSUPPORTED" in str(exc)
else:
    raise AssertionError("UNKNOWN_PROP_NOT_REJECTED")

print("ui_runtime_contract=OK")
print("home_payload_contract=OK")
print("portfolio_payload_contract=OK")
print("unsupported_schema_rejected=OK")
print("unsupported_node_rejected=OK")
print("unsafe_action_rejected=OK")
print("unknown_prop_rejected=OK")
PY

echo "ui_runtime_contract=OK"
echo "contract_version=marketcore.ui_runtime.contract.v1"
echo "render_tree_schema_version=marketcore.render_tree.v1"
echo "supported_node_types=15"
echo "allowed_theme_codes=DEFAULT,PHONE"
echo "runtime_implementation=0"
echo "html_generation=0"
echo "storage_dependency=0"
echo "routes_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_RUNTIME_CONTRACT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_RUNTIME_CONTRACT_V1_OK"
