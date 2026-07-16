"use strict";

(function installMarketCoreBrowserActionControllerV2(globalObject) {
    const CONTROLLER_VERSION = "marketcore.browser_action_controller.v2";

    function createRequestId() {
        if (globalObject.crypto && typeof globalObject.crypto.randomUUID === "function") {
            return globalObject.crypto.randomUUID();
        }
        if (!globalObject.crypto || typeof globalObject.crypto.getRandomValues !== "function") {
            throw new Error("ACTION_REQUEST_ID_GENERATOR_UNAVAILABLE");
        }
        const bytes = globalObject.crypto.getRandomValues(new Uint8Array(16));
        bytes[6] = (bytes[6] & 0x0f) | 0x40;
        bytes[8] = (bytes[8] & 0x3f) | 0x80;
        const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0"));
        return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex.slice(6, 8).join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10).join("")}`;
    }

    function create(options) {
        if (!options || typeof options !== "object") throw new Error("ACTION_CONTROLLER_OPTIONS_REQUIRED");
        const endpoint = options.endpoint || "/api/v2/actions/dispatch";
        const onNavigation = typeof options.onNavigation === "function" ? options.onNavigation : () => {};
        const onCommand = typeof options.onCommand === "function" ? options.onCommand : () => {};
        return async function actionSink(intent) {
            const requestId = intent.requestId || createRequestId();
            const response = await globalObject.fetch(endpoint, {
                method: "POST",
                headers: {"Content-Type": "application/json", "Accept": "application/json"},
                credentials: "same-origin",
                cache: "no-store",
                body: JSON.stringify({...intent, requestId})
            });
            const result = await response.json();
            if (!response.ok) throw new Error(`ACTION_DISPATCH_FAILED:${result.reason_code || response.status}`);
            if (result.status === "NAVIGATED") await onNavigation(result.target_id, result);
            else await onCommand(result, intent);
            return result;
        };
    }

    globalObject.MarketCoreBrowserActionControllerV2 = Object.freeze({controllerVersion: CONTROLLER_VERSION, create});
})(globalThis);
