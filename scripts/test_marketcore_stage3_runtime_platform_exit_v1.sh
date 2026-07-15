#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core

assets=(
  render_tree_validator_v2.js
  domain_render_tree_runtime_v2.js
  browser_platform_driver_v2.js
  browser_presentation_services_v2.js
  browser_bootstrap_v2.js
)
for asset in "${assets[@]}"; do
  node --check "src/marketcore/presentation/ui_runtime/assets/v2/$asset"
done

cat >/tmp/test_marketcore_stage3_runtime_platform_exit_v1.js <<'JS'
"use strict";
const root = "/opt/finam-core/src/marketcore/presentation/ui_runtime/assets/v2/";
for (const asset of ["render_tree_validator_v2.js", "domain_render_tree_runtime_v2.js", "browser_platform_driver_v2.js", "browser_presentation_services_v2.js", "browser_bootstrap_v2.js"]) require(root + asset);

class Element {
  constructor(tagName) { this.tagName = tagName; this.attributes = {}; this.children = []; this.textContent = ""; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren() { this.children = []; }
}
class Document { createElement(tagName) { return new Element(tagName); } }

const catalog = {schema_version: "marketcore.i18n_catalog.v2", locale_code: "ru-RU", fallback_locale_code: "ru-RU", messages: {"test.title": "Проверка Runtime V2", "test.ready": "Готово {count}"}};
const tree = {
  schema_version: "marketcore.render_tree.v2", document_id: "stage3.exit.v1",
  locale_code: "ru-RU", fallback_locale_code: "ru-RU", timezone_code: "Europe/Moscow",
  generated_at: "2026-07-15T12:00:00Z", source_as_of: "2026-07-15T11:59:00Z", quality_code: "VERIFIED",
  root: {type: "workspace", node_id: "root", children: [{type: "page", node_id: "page", children: [
    {type: "title", node_id: "title", content: {message_key: "test.title", level_code: "PAGE"}, children: []},
    {type: "metric_value", node_id: "ready", content: {message_key: "test.ready", message_args: {count: 5}}, children: []},
    {type: "metric_value", node_id: "duration", content: {value: 7500, format_code: "DURATION_HM"}, children: []}
  ]}]}
};

globalThis.fetch = async (url) => ({
  ok: true, status: 200,
  headers: {get: () => String(url).startsWith("/api/v2/i18n/") ? "application/vnd.marketcore.i18n-catalog+json; charset=utf-8" : "application/vnd.marketcore.render-tree+json; charset=utf-8"},
  json: async () => String(url).startsWith("/api/v2/i18n/") ? catalog : tree
});

(async () => {
  const services = await globalThis.MarketCoreBrowserPresentationServicesV2.load({localeCode: "ru-RU"});
  const mount = new Element("mount");
  const result = await globalThis.MarketCoreBrowserBootstrapV2.start({
    endpoint: "/api/v2/domain-render-tree/home", documentObject: new Document(), mountElement: mount,
    translate: services.translate, format: services.format
  });
  if (!result.success || result.nodesProcessed !== 5) throw new Error("STAGE3_EXECUTION_FAILED");
  const page = mount.children[0].children[0];
  if (page.children[0].textContent !== "Проверка Runtime V2") throw new Error("STAGE3_I18N_FAILED");
  if (page.children[1].textContent !== "Готово 5") throw new Error("STAGE3_ARGUMENTS_FAILED");
  if (page.children[2].textContent !== "2 ч 5 мин") throw new Error("STAGE3_DURATION_FAILED");
  console.log("STAGE3_RUNTIME_PLATFORM_EXIT_OK");
})().catch(error => { console.error(error); process.exit(1); });
JS

TZ=UTC node /tmp/test_marketcore_stage3_runtime_platform_exit_v1.js

runtime=src/marketcore/presentation/ui_runtime/assets/v2/domain_render_tree_runtime_v2.js
if grep -nE 'document\.|createElement|appendChild|replaceChildren|innerHTML|outerHTML|fetch\(|XMLHttpRequest|WebSocket|className|setAttribute.*class|\.style' "$runtime"; then
  echo STAGE3_RUNTIME_PLATFORM_LEAK_FOUND
  exit 1
fi
if find src/marketcore/presentation/ui_runtime/assets/v2 -type f \( -name '*.html' -o -name '*.css' \) | grep .; then
  echo STAGE3_HTML_CSS_ASSET_FOUND
  exit 1
fi

for endpoint in home portfolio control-center; do
  curl -fsS "http://127.0.0.1:8080/api/v2/domain-render-tree/$endpoint" >/dev/null
done
curl -fsS 'http://127.0.0.1:8080/api/v2/i18n/catalog?locale=ru-RU' >/dev/null

echo platform_semantics_in_runtime=0
echo html_assets=0
echo css_assets=0
echo live_domain_endpoints=3
echo i18n_live_cutover_debt=OPEN
echo VERDICT=MARKETCORE_STAGE3_RUNTIME_PLATFORM_COMPLETE
