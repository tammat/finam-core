"use strict";

(function startControlCenterRuntimeV2(globalObject) {
    const mount = globalObject.document.getElementById("marketcore-control-center-runtime-root");
    const executor = globalObject.MarketCoreBrowserRenderTreeExecutorV1;

    async function start() {
        try {
            const response = await globalObject.fetch("/api/v2/render-tree/control-center/edge", {
                headers: {Accept: "application/json"},
                credentials: "same-origin",
                cache: "no-store"
            });
            if (!response.ok) throw new Error(`HTTP_${response.status}`);
            const payload = await response.json();
            const result = executor.executeRenderTree(payload, {
                documentObject: globalObject.document,
                mountElement: mount
            });
            if (!result.success) throw new Error(result.diagnostics.join("|"));
            mount.setAttribute("data-runtime-status", "READY");
            mount.setAttribute("data-runtime-version", "marketcore.control_center.runtime.v2");
        } catch (error) {
            mount.textContent = "Не удалось загрузить центр управления.";
            mount.setAttribute("data-runtime-status", "FAILED");
            mount.setAttribute("data-runtime-error", String(error && error.message ? error.message : error));
        }
    }

    start();
})(window);
