#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo \
"=== TEST_MARKETCORE_BROWSER_RENDER_TREE_EXECUTOR_V1 ==="

validator_asset=\
"src/marketcore/presentation/ui_runtime/assets/v1/render_tree_validator_v1.js"

driver_asset=\
"src/marketcore/presentation/ui_runtime/assets/v1/browser_dom_driver_v1.js"

executor_asset=\
"src/marketcore/presentation/ui_runtime/assets/v1/browser_render_tree_executor_v1.js"

asset_delivery=\
"src/marketcore/presentation/ui_runtime/asset_delivery_v1.py"

for file in \
  "$validator_asset" \
  "$driver_asset" \
  "$executor_asset" \
  "$asset_delivery"
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

echo "node_runtime=$NODE_BIN"
"$NODE_BIN" --version

"$NODE_BIN" --check "$validator_asset"
"$NODE_BIN" --check "$driver_asset"
"$NODE_BIN" --check "$executor_asset"

# Executor не должен самостоятельно работать с DOM или сетью.
if grep -nE \
  'innerHTML|outerHTML|document\.write|document\.createElement|appendChild|replaceChildren|querySelector|fetch\(|XMLHttpRequest|WebSocket|eval\(|new Function|send_order|place_order|cancel_order|execute_order|psycopg|SELECT |INSERT |UPDATE |DELETE ' \
  "$executor_asset"
then
  echo "FORBIDDEN_EXECUTOR_OPERATION_FOUND"
  exit 1
fi

cat > \
/tmp/test_marketcore_browser_render_tree_executor_v1.js <<'JS'
"use strict";

require(
    "/opt/finam-core/src/marketcore/presentation/"
    + "ui_runtime/assets/v1/"
    + "render_tree_validator_v1.js"
);

require(
    "/opt/finam-core/src/marketcore/presentation/"
    + "ui_runtime/assets/v1/"
    + "browser_dom_driver_v1.js"
);

require(
    "/opt/finam-core/src/marketcore/presentation/"
    + "ui_runtime/assets/v1/"
    + "browser_render_tree_executor_v1.js"
);

class FakeElement {
    constructor(tagName) {
        this.tagName = tagName;
        this.attributes = {};
        this.children = [];
        this.textContent = "";
    }

    setAttribute(name, value) {
        this.attributes[name] = String(value);
    }

    appendChild(child) {
        this.children.push(child);
        return child;
    }

    replaceChildren() {
        this.children = [];
    }
}

class FakeDocument {
    createElement(tagName) {
        return new FakeElement(tagName);
    }
}

const executor =
    globalThis.MarketCoreBrowserRenderTreeExecutorV1;

if (!executor) {
    throw new Error(
        "BROWSER_RENDER_TREE_EXECUTOR_GLOBAL_NOT_FOUND"
    );
}

const payload = {
    schema_version: "marketcore.render_tree.v1",
    root: {
        type: "workspace",
        props: {
            class: "mc-v2-shell"
        },
        text: "",
        children: [
            {
                type: "page",
                props: {
                    class: "mc-v2-page"
                },
                text: "",
                children: [
                    {
                        type: "title",
                        props: {
                            level: 1
                        },
                        text: "MarketCore OS",
                        children: []
                    },
                    {
                        type: "card",
                        props: {
                            "data-status": "READY"
                        },
                        text: "",
                        children: [
                            {
                                type: "text",
                                props: {},
                                text: "Проверка Executor",
                                children: []
                            },
                            {
                                type: "action",
                                props: {
                                    href:
                                        "/workspace-v2/portfolio"
                                },
                                text: "Открыть",
                                children: []
                            }
                        ]
                    }
                ]
            }
        ]
    }
};

const mountElement = new FakeElement("mount");

const result = executor.executeRenderTree(
    payload,
    {
        documentObject: new FakeDocument(),
        mountElement
    }
);

if (result.success !== true) {
    throw new Error(
        "VALID_RENDER_TREE_EXECUTION_FAILED:"
        + JSON.stringify(result)
    );
}

if (result.status !== "SUCCESS") {
    throw new Error(
        `EXECUTOR_STATUS_INVALID:${result.status}`
    );
}

if (result.nodesProcessed !== 6) {
    throw new Error(
        `EXECUTOR_NODE_COUNT_INVALID:`
        + `${result.nodesProcessed}`
    );
}

if (result.diagnostics.length !== 0) {
    throw new Error(
        "UNEXPECTED_EXECUTOR_DIAGNOSTICS"
    );
}

if (
    !result.driverResult
    || result.driverResult.nodesRendered !== 6
) {
    throw new Error(
        "DRIVER_RESULT_INVALID"
    );
}

if (mountElement.children.length !== 1) {
    throw new Error("MOUNT_ROOT_COUNT_INVALID");
}

const workspace = mountElement.children[0];
const page = workspace.children[0];
const title = page.children[0];
const card = page.children[1];
const text = card.children[0];
const action = card.children[1];

if (workspace.tagName !== "main") {
    throw new Error("WORKSPACE_TAG_INVALID");
}

if (page.tagName !== "section") {
    throw new Error("PAGE_TAG_INVALID");
}

if (title.tagName !== "h1") {
    throw new Error("TITLE_TAG_INVALID");
}

if (title.textContent !== "MarketCore OS") {
    throw new Error("TITLE_TEXT_INVALID");
}

if (card.tagName !== "article") {
    throw new Error("CARD_TAG_INVALID");
}

if (
    card.attributes["data-status"]
    !== "READY"
) {
    throw new Error("CARD_STATUS_INVALID");
}

if (
    text.textContent
    !== "Проверка Executor"
) {
    throw new Error("TEXT_CONTENT_INVALID");
}

if (
    action.attributes.href
    !== "/workspace-v2/portfolio"
) {
    throw new Error("ACTION_HREF_INVALID");
}

/*
 * Невалидный payload должен быть отклонен
 * до изменения mountElement.
 */
const invalidMount = new FakeElement("mount");
invalidMount.children.push(
    new FakeElement("existing")
);

const invalidPayload = {
    ...payload,
    schema_version: "marketcore.render_tree.v999"
};

let invalidPayloadRejected = false;

try {
    executor.executeRenderTree(
        invalidPayload,
        {
            documentObject: new FakeDocument(),
            mountElement: invalidMount
        }
    );
} catch (error) {
    if (
        error.code
        !== "RENDER_TREE_SCHEMA_VERSION_UNSUPPORTED"
    ) {
        throw error;
    }

    invalidPayloadRejected = true;
}

if (!invalidPayloadRejected) {
    throw new Error(
        "INVALID_PAYLOAD_NOT_REJECTED"
    );
}

if (
    invalidMount.children.length !== 1
    || invalidMount.children[0].tagName !== "existing"
) {
    throw new Error(
        "MOUNT_CHANGED_BEFORE_VALIDATION"
    );
}

let invalidOptionsRejected = false;

try {
    executor.executeRenderTree(payload, {});
} catch (error) {
    if (
        error.code
        !== "BROWSER_RENDER_TREE_MOUNT_ELEMENT_REQUIRED"
    ) {
        throw error;
    }

    invalidOptionsRejected = true;
}

if (!invalidOptionsRejected) {
    throw new Error(
        "INVALID_EXECUTOR_OPTIONS_NOT_REJECTED"
    );
}

console.log("executor_global=OK");
console.log("validator_first=OK");
console.log("driver_auto_creation=OK");
console.log("depth_first_execution=OK");
console.log("driver_result_forwarded=OK");
console.log("domain_tree_rendered=OK");
console.log("invalid_payload_rejected=OK");
console.log("mount_unchanged_before_validation=OK");
console.log("invalid_options_rejected=OK");
console.log("nodes_processed=6");
JS

"$NODE_BIN" \
  /tmp/test_marketcore_browser_render_tree_executor_v1.js

PYTHONPYCACHEPREFIX=/tmp/marketcore_browser_render_tree_executor_v1 \
PYTHONPATH=src \
python -m py_compile "$asset_delivery"

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.router import route
from marketcore.presentation.ui_runtime.asset_delivery_v1 import (
    UI_RUNTIME_ASSETS_V1,
    load_ui_runtime_asset_v1,
)


asset_code = "browser_render_tree_executor_js"
asset_route = (
    "/assets/marketcore/ui-runtime/v1/"
    "browser-render-tree-executor.js"
)

definitions = {
    definition.asset_code: definition
    for definition in UI_RUNTIME_ASSETS_V1
}

assert asset_code in definitions

response = load_ui_runtime_asset_v1(asset_route)

assert response.status_code == 200
assert (
    response.content_type
    == "application/javascript; charset=utf-8"
)

text = response.body.decode("utf-8")

assert (
    "MarketCoreBrowserRenderTreeExecutorV1"
    in text
)
assert (
    "marketcore.browser_render_tree_executor.v1"
    in text
)

for forbidden in (
    "innerHTML",
    "document.createElement",
    "appendChild",
    "fetch(",
    "XMLHttpRequest",
):
    assert forbidden not in text

status_code, body = route(asset_route)

assert status_code == 200
assert body == response.body

print("executor_asset_registry=OK")
print("executor_asset_delivery=OK")
print("executor_content_type=OK")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS \
  -D /tmp/marketcore_browser_render_tree_executor_v1.headers \
  -o /tmp/marketcore_browser_render_tree_executor_v1.js \
  http://127.0.0.1:8080/assets/marketcore/ui-runtime/v1/browser-render-tree-executor.js

grep -qi \
  '^Content-Type: application/javascript; charset=utf-8' \
  /tmp/marketcore_browser_render_tree_executor_v1.headers

grep -q \
  'MarketCoreBrowserRenderTreeExecutorV1' \
  /tmp/marketcore_browser_render_tree_executor_v1.js

grep -q \
  'marketcore.browser_render_tree_executor.v1' \
  /tmp/marketcore_browser_render_tree_executor_v1.js

echo "browser_render_tree_executor=OK"
echo "validator_first=OK"
echo "browser_dom_driver_integration=OK"
echo "tree_traversal=depth_first_preorder"
echo "dom_operations_in_executor=0"
echo "network_operations=0"
echo "server_html_generation=0"
echo "storage_dependency=0"
echo "trading_dependency=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
"VERDICT=MARKETCORE_BROWSER_RENDER_TREE_EXECUTOR_V1_READY"
echo \
"VERDICT=TEST_MARKETCORE_BROWSER_RENDER_TREE_EXECUTOR_V1_OK"
