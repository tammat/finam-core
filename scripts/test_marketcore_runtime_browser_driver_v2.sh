#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core

root=src/marketcore/presentation/ui_runtime/assets/v2
validator="$root/render_tree_validator_v2.js"
runtime="$root/domain_render_tree_runtime_v2.js"
driver="$root/browser_platform_driver_v2.js"

for file in "$validator" "$runtime" "$driver"; do test -f "$file"; node --check "$file"; done

if grep -nE 'document\.|createElement|appendChild|replaceChildren|innerHTML|outerHTML|fetch\(|XMLHttpRequest|WebSocket|className|setAttribute.*class|\.style' "$runtime"; then
  echo RUNTIME_V2_PLATFORM_SEMANTICS_FORBIDDEN
  exit 1
fi

cat >/tmp/test_marketcore_runtime_browser_driver_v2.js <<'JS'
"use strict";
require("/opt/finam-core/src/marketcore/presentation/ui_runtime/assets/v2/render_tree_validator_v2.js");
require("/opt/finam-core/src/marketcore/presentation/ui_runtime/assets/v2/domain_render_tree_runtime_v2.js");
require("/opt/finam-core/src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js");

class Element {
    constructor(tagName) { this.tagName = tagName; this.attributes = {}; this.children = []; this.textContent = ""; }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    appendChild(child) { this.children.push(child); return child; }
    replaceChildren() { this.children = []; }
}
class Document { createElement(tagName) { return new Element(tagName); } }

const payload = {
    schema_version: "marketcore.render_tree.v2",
    document_id: "test.home.v2", locale_code: "ru-RU", fallback_locale_code: "ru-RU",
    timezone_code: "Europe/Moscow", generated_at: "2026-07-15T12:00:00Z",
    source_as_of: "2026-07-15T11:59:00Z", quality_code: "VERIFIED",
    root: {type: "workspace", node_id: "workspace", children: [
        {type: "page", node_id: "page", children: [
            {type: "title", node_id: "title", content: {message_key: "home.title", level_code: "PAGE"}, children: []},
            {type: "metric_value", node_id: "duration", content: {value: 3900, format_code: "DURATION_HM"}, children: []}
        ]}
    ]}
};

const mount = new Element("mount");
const driver = new globalThis.MarketCoreBrowserPlatformDriverV2.Driver({documentObject: new Document(), mountElement: mount});
const result = globalThis.MarketCoreDomainRenderTreeRuntimeV2.execute(payload, {
    validator: globalThis.MarketCoreRenderTreeValidatorV2,
    driver,
    translate: (key) => ({"home.title": "Рабочий стол"})[key],
    format: (value, code) => code === "DURATION_HM" ? "1 ч 5 мин" : String(value)
});

if (!result.success || result.nodesProcessed !== 4 || result.driverResult.nodesRendered !== 4) throw new Error("EXECUTION_RESULT_INVALID");
const workspace = mount.children[0];
const page = workspace.children[0];
if (workspace.tagName !== "main" || page.tagName !== "section") throw new Error("PLATFORM_MAPPING_INVALID");
if (page.children[0].tagName !== "h1" || page.children[0].textContent !== "Рабочий стол") throw new Error("MESSAGE_RESOLUTION_INVALID");
if (page.children[1].textContent !== "1 ч 5 мин") throw new Error("DURATION_FORMAT_INVALID");

const invalidMount = new Element("mount");
invalidMount.appendChild(new Element("existing"));
let rejected = false;
try {
    const invalidDriver = new globalThis.MarketCoreBrowserPlatformDriverV2.Driver({documentObject: new Document(), mountElement: invalidMount});
    globalThis.MarketCoreDomainRenderTreeRuntimeV2.execute({...payload, schema_version: "bad"}, {
        validator: globalThis.MarketCoreRenderTreeValidatorV2, driver: invalidDriver,
        translate: String, format: String
    });
} catch (error) { rejected = error.code === "RENDER_TREE_V2_SCHEMA_VERSION_UNSUPPORTED"; }
if (!rejected || invalidMount.children[0].tagName !== "existing") throw new Error("VALIDATE_BEFORE_PLATFORM_MUTATION_FAILED");
console.log("RUNTIME_BROWSER_DRIVER_V2_OK");
JS

node /tmp/test_marketcore_runtime_browser_driver_v2.js
echo MARKETCORE_RUNTIME_BROWSER_DRIVER_V2_OK
