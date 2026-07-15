"use strict";

(function installMarketCoreBrowserActionControllerV2(globalObject) {
    const CONTROLLER_VERSION = "marketcore.browser_action_controller.v2";

    function create(options) {
        if (!options || typeof options !== "object") throw new Error("ACTION_CONTROLLER_OPTIONS_REQUIRED");
        const endpoint = options.endpoint || "/api/v2/actions/dispatch";
        const onNavigation = typeof options.onNavigation === "function" ? options.onNavigation : () => {};
        return async function actionSink(intent) {
            const response = await globalObject.fetch(endpoint, {
                method: "POST",
                headers: {"Content-Type": "application/json", "Accept": "application/json"},
                credentials: "same-origin",
                cache: "no-store",
                body: JSON.stringify(intent)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(`ACTION_DISPATCH_FAILED:${result.reason_code || response.status}`);
            if (result.status === "NAVIGATED") await onNavigation(result.target_id, result);
            return result;
        };
    }

    globalObject.MarketCoreBrowserActionControllerV2 = Object.freeze({controllerVersion: CONTROLLER_VERSION, create});
})(globalThis);
