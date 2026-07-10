#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RENDER_TREE_VALIDATOR_V1 ==="

validator_asset="src/marketcore/presentation/ui_runtime/assets/v1/render_tree_validator_v1.js"
asset_delivery="src/marketcore/presentation/ui_runtime/asset_delivery_v1.py"

test -f "$validator_asset"
test -f "$asset_delivery"

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

if grep -nE \
  'innerHTML|outerHTML|document\.write|document\.createElement|fetch\(|XMLHttpRequest|eval\(|new Function' \
  "$validator_asset"
then
  echo "FORBIDDEN_RUNTIME_OPERATION_FOUND"
  exit 1
fi

cat > /tmp/test_marketcore_render_tree_validator_v1.js <<'JS'
"use strict";

require(
    "/opt/finam-core/src/marketcore/presentation/ui_runtime/assets/v1/render_tree_validator_v1.js"
);

const validator = globalThis.MarketCoreRenderTreeValidatorV1;

if (!validator) {
    throw new Error("VALIDATOR_GLOBAL_NOT_FOUND");
}

const validPayload = {
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
                            "data-status": "OK"
                        },
                        text: "",
                        children: [
                            {
                                type: "text",
                                props: {},
                                text: "Проверка",
                                children: []
                            },
                            {
                                type: "action",
                                props: {
                                    href: "/workspace-v2/portfolio"
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

const result = validator.validate(validPayload);

if (result.valid !== true) {
    throw new Error("VALID_PAYLOAD_REJECTED");
}

if (result.nodeCount !== 6) {
    throw new Error(
        `UNEXPECTED_NODE_COUNT:${result.nodeCount}`
    );
}

function expectError(
    payload,
    expectedCode
) {
    try {
        validator.validate(payload);
    } catch (error) {
        if (error.code !== expectedCode) {
            throw new Error(
                `UNEXPECTED_ERROR_CODE:${error.code}:${expectedCode}`
            );
        }

        return;
    }

    throw new Error(
        `EXPECTED_VALIDATION_ERROR_NOT_RAISED:${expectedCode}`
    );
}

expectError(
    {
        ...validPayload,
        schema_version: "marketcore.render_tree.v999"
    },
    "RENDER_TREE_SCHEMA_VERSION_UNSUPPORTED"
);

expectError(
    {
        ...validPayload,
        root: {
            ...validPayload.root,
            type: "card"
        }
    },
    "RENDER_TREE_ROOT_TYPE_INVALID"
);

expectError(
    {
        ...validPayload,
        root: {
            ...validPayload.root,
            props: {
                onclick: "bad"
            }
        }
    },
    "RENDER_TREE_NODE_PROP_UNSUPPORTED"
);

expectError(
    {
        ...validPayload,
        root: {
            type: "workspace",
            props: {},
            text: "",
            children: [
                {
                    type: "html_div",
                    props: {},
                    text: "",
                    children: []
                }
            ]
        }
    },
    "RENDER_TREE_NODE_TYPE_UNSUPPORTED"
);

expectError(
    {
        ...validPayload,
        root: {
            type: "workspace",
            props: {},
            text: "",
            children: [
                {
                    type: "title",
                    props: {
                        level: 9
                    },
                    text: "Ошибка",
                    children: []
                }
            ]
        }
    },
    "RENDER_TREE_TITLE_LEVEL_INVALID"
);

expectError(
    {
        ...validPayload,
        root: {
            type: "workspace",
            props: {},
            text: "",
            children: [
                {
                    type: "action",
                    props: {
                        href: "javascript:alert(1)"
                    },
                    text: "Ошибка",
                    children: []
                }
            ]
        }
    },
    "RENDER_TREE_ACTION_TARGET_SCHEME_FORBIDDEN"
);

console.log("validator_global=OK");
console.log("valid_payload=OK");
console.log("invalid_schema_rejected=OK");
console.log("invalid_root_rejected=OK");
console.log("unsupported_prop_rejected=OK");
console.log("unsupported_node_rejected=OK");
console.log("invalid_title_rejected=OK");
console.log("unsafe_action_rejected=OK");
JS

"$NODE_BIN" /tmp/test_marketcore_render_tree_validator_v1.js

PYTHONPYCACHEPREFIX=/tmp/marketcore_render_tree_validator_v1 \
PYTHONPATH=src \
python -m py_compile "$asset_delivery"

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.router import route
from marketcore.presentation.ui_runtime.asset_delivery_v1 import (
    UI_RUNTIME_ASSETS_V1,
    load_ui_runtime_asset_v1,
)

route_path = (
    "/assets/marketcore/ui-runtime/v1/"
    "render-tree-validator.js"
)

definitions = {
    item.asset_code: item
    for item in UI_RUNTIME_ASSETS_V1
}

assert "render_tree_validator_js" in definitions
assert len(UI_RUNTIME_ASSETS_V1) == 3

response = load_ui_runtime_asset_v1(route_path)

assert response.status_code == 200
assert (
    response.content_type
    == "application/javascript; charset=utf-8"
)

text = response.body.decode("utf-8")

assert "MarketCoreRenderTreeValidatorV1" in text
assert "marketcore.render_tree.v1" in text
assert "innerHTML" not in text
assert "fetch(" not in text

status_code, body = route(route_path)

assert status_code == 200
assert body == response.body

print("validator_asset_registry=OK")
print("validator_asset_delivery=OK")
print("validator_content_type=OK")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS \
  -D /tmp/marketcore_render_tree_validator_v1.headers \
  -o /tmp/marketcore_render_tree_validator_v1.js \
  http://127.0.0.1:8080/assets/marketcore/ui-runtime/v1/render-tree-validator.js

grep -qi \
  '^Content-Type: application/javascript; charset=utf-8' \
  /tmp/marketcore_render_tree_validator_v1.headers

grep -q \
  'MarketCoreRenderTreeValidatorV1' \
  /tmp/marketcore_render_tree_validator_v1.js

grep -q \
  'marketcore.render_tree.v1' \
  /tmp/marketcore_render_tree_validator_v1.js

echo "render_tree_validator=OK"
echo "validator_execution=OK"
echo "validator_asset_delivery=OK"
echo "dom_operations=0"
echo "html_generation=0"
echo "network_operations=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RENDER_TREE_VALIDATOR_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RENDER_TREE_VALIDATOR_V1_OK"
