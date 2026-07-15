#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
asset=src/marketcore/presentation/ui_runtime/assets/v2/browser_presentation_services_v2.js
node --check "$asset"
cat >/tmp/test_marketcore_browser_presentation_services_v2.js <<'JS'
"use strict";
require("/opt/finam-core/src/marketcore/presentation/ui_runtime/assets/v2/browser_presentation_services_v2.js");
const service = globalThis.MarketCoreBrowserPresentationServicesV2;
const translate = service.createTranslator({
  schema_version: "marketcore.i18n_catalog.v2",
  messages: {ready: "Готово {ready} из {total}"}
});
if (translate("ready", {ready: 15, total: 15}, "ru-RU") !== "Готово 15 из 15") throw new Error("TRANSLATION_INVALID");
let missingRejected = false;
try { translate("missing", {}, "ru-RU"); } catch (error) { missingRejected = error.code === "PRESENTATION_V2_MESSAGE_MISSING"; }
if (!missingRejected) throw new Error("MISSING_TRANSLATION_NOT_REJECTED");
const format = service.createFormatter();
if (format(3900, "DURATION_HM", "ru-RU", "Europe/Moscow") !== "1 ч 5 мин") throw new Error("DURATION_INVALID");
if (!format("2026-07-15T12:00:00Z", "DATETIME", "ru-RU", "Europe/Moscow").includes("15:00:00")) throw new Error("MOSCOW_TIME_INVALID");
if (!format("0.125", "PERCENT_RATIO", "ru-RU", "Europe/Moscow").includes("12,5")) throw new Error("PERCENT_INVALID");
console.log("BROWSER_PRESENTATION_SERVICES_V2_OK");
JS
TZ=UTC node /tmp/test_marketcore_browser_presentation_services_v2.js
