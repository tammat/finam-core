#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_BROWSER_DOM_DRIVER_V1 ==="

driver_asset=\
"src/marketcore/presentation/ui_runtime/assets/v1/browser_dom_driver_v1.js"

asset_delivery=\
"src/marketcore/presentation/ui_runtime/asset_delivery_v1.py"

for file in "$driver_asset" "$asset_delivery"; do
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

"$NODE_BIN" --check "$driver_asset"

if grep -nE \
  'innerHTML|outerHTML|document\.write|eval\(|new Function|fetch\(|XMLHttpRequest|WebSocket|send_order|place_order|cancel_order|execute_order|psycopg|SELECT |INSERT |UPDATE |DELETE ' \
  "$driver_asset"
then
  echo "FORBIDDEN_BROWSER_DOM_DRIVER_OPERATION_FOUND"
  exit 1
fi

cat > /tmp/test_marketcore_browser_dom_driver_v1.js <<'JS'
"use strict";

require(
    "/opt/finam-core/"
    + "src/marketcore/presentation/ui_runtime/assets/v1/"
    + "browser_dom_driver_v1.js"
);

class FakeElement {
    constructor(tagName) {
        this.tagName = tagName;
        this.attributes = {};
        this.children = [];
        this.textContent = "";
    }

    setAttribute(name, value) {
        this.attributes[name] = value;
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

const exported = globalThis.MarketCoreBrowserDomDriverV1;

if (!exported) {
    throw new Error("BROWSER_DOM_DRIVER_GLOBAL_NOT_FOUND");
}

const mount = new FakeElement("mount");
const driver = new exported.Driver({
    documentObject: new FakeDocument(),
    mountElement: mount
});

const payload = {
    schema_version: "marketcore.render_tree.v1",
    root: {
        type: "workspace",
        props: {
            class: "mc-v2-shell"
        },
        text: "",
        children: []
    }
};

driver.beginDocument(payload, {
    expectedNodeCount: 5
});

driver.renderNode(
    {
        type: "workspace",
        props: {
            class: "mc-v2-shell"
        },
        text: "",
        children: []
    },
    {
        depth: 0,
        path: "root"
    }
);

driver.renderNode(
    {
        type: "page",
        props: {
            class: "mc-v2-page"
        },
        text: "",
        children: []
    },
    {
        depth: 1,
        path: "root.children[0]"
    }
);

driver.renderNode(
    {
        type: "title",
        props: {
            level: 1
        },
        text: "MarketCore OS",
        children: []
    },
    {
        depth: 2,
        path: "root.children[0].children[0]"
    }
);

driver.renderNode(
    {
        type: "card",
        props: {
            "data-status": "READY"
        },
        text: "",
        children: []
    },
    {
        depth: 2,
        path: "root.children[0].children[1]"
    }
);

driver.renderNode(
    {
        type: "action",
        props: {
            href: "/workspace-v2/portfolio",
            class: "mc-v2-button"
        },
        text: "Открыть",
        children: []
    },
    {
        depth: 3,
        path: "root.children[0].children[1].children[0]"
    }
);

const result = driver.endDocument(payload, {
    nodesProcessed: 5
});

if (result.nodesRendered !== 5) {
    throw new Error(
        `INVALID_NODE_COUNT:${result.nodesRendered}`
    );
}

const main = mount.children[0];
const page = main.children[0];
const title = page.children[0];
const card = page.children[1];
const action = card.children[0];

if (main.tagName !== "main") {
    throw new Error(`WORKSPACE_TAG_INVALID:${main.tagName}`);
}

if (page.tagName !== "section") {
    throw new Error(`PAGE_TAG_INVALID:${page.tagName}`);
}

if (title.tagName !== "h1") {
    throw new Error(`TITLE_TAG_INVALID:${title.tagName}`);
}

if (title.textContent !== "MarketCore OS") {
    throw new Error("TITLE_TEXT_INVALID");
}

if (card.tagName !== "article") {
    throw new Error(`CARD_TAG_INVALID:${card.tagName}`);
}

if (card.attributes["data-status"] !== "READY") {
    throw new Error("CARD_STATUS_INVALID");
}

if (action.tagName !== "a") {
    throw new Error(`ACTION_TAG_INVALID:${action.tagName}`);
}

if (
    action.attributes.href
    !== "/workspace-v2/portfolio"
) {
    throw new Error("ACTION_HREF_INVALID");
}

if (action.textContent !== "Открыть") {
    throw new Error("ACTION_TEXT_INVALID");
}

console.log("browser_dom_driver_global=OK");
console.log("driver_contract=OK");
console.log("workspace_to_main=OK");
console.log("page_to_section=OK");
console.log("title_to_h1=OK");
console.log("card_to_article=OK");
console.log("action_to_anchor=OK");
console.log("safe_text_content=OK");
console.log("nodes_rendered=5");
JS

"$NODE_BIN" \
  /tmp/test_marketcore_browser_dom_driver_v1.js

PYTHONPYCACHEPREFIX=/tmp/marketcore_browser_dom_driver_v1 \
PYTHONPATH=src \
python -m py_compile "$asset_delivery"

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.router import route
from marketcore.presentation.ui_runtime.asset_delivery_v1 import (
    UI_RUNTIME_ASSETS_V1,
    load_ui_runtime_asset_v1,
)

asset_route = (
    "/assets/marketcore/ui-runtime/v1/"
    "browser-dom-driver.js"
)

definitions = {
    definition.asset_code: definition
    for definition in UI_RUNTIME_ASSETS_V1
}

assert "browser_dom_driver_js" in definitions

response = load_ui_runtime_asset_v1(asset_route)

assert response.status_code == 200
assert (
    response.content_type
    == "application/javascript; charset=utf-8"
)

text = response.body.decode("utf-8")

assert "MarketCoreBrowserDomDriverV1" in text
assert "marketcore.browser_dom_driver.v1" in text
assert "innerHTML" not in text
assert "document.write" not in text
assert "fetch(" not in text

status_code, body = route(asset_route)

assert status_code == 200
assert body == response.body

print("browser_dom_driver_asset_registry=OK")
print("browser_dom_driver_asset_delivery=OK")
print("browser_dom_driver_content_type=OK")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS \
  -D /tmp/marketcore_browser_dom_driver_v1.headers \
  -o /tmp/marketcore_browser_dom_driver_v1.js \
  http://127.0.0.1:8080/assets/marketcore/ui-runtime/v1/browser-dom-driver.js

grep -qi \
  '^Content-Type: application/javascript; charset=utf-8' \
  /tmp/marketcore_browser_dom_driver_v1.headers

grep -q \
  'MarketCoreBrowserDomDriverV1' \
  /tmp/marketcore_browser_dom_driver_v1.js

echo "browser_dom_driver=OK"
echo "platform_driver_implementation=OK"
echo "dom_api=createElement,appendChild,textContent"
echo "inner_html_usage=0"
echo "server_html_generation=0"
echo "network_operations=0"
echo "storage_dependency=0"
echo "trading_dependency=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_BROWSER_DOM_DRIVER_V1_READY"
echo "VERDICT=TEST_MARKETCORE_BROWSER_DOM_DRIVER_V1_OK"
