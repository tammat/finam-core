"use strict";

(function startControlCenterRuntimeV2(globalObject) {
    const mount = globalObject.document.getElementById("marketcore-control-center-runtime-root");
    const executor = globalObject.MarketCoreBrowserRenderTreeExecutorV1;
    const REFRESH_INTERVAL_MS = 30000;
    const SECTION_BY_ROUTE = {
        "data-quality": "market-prerequisites",
        "commodity-factors": "volatility-analysis",
        "discover": "entry-analysis",
        "lead-lag": "relationship-factory",
        "relationship-factory": "relationship-factory",
        "relationship-pipeline": "relationship-factory",
        "signal-funnel": "signal-funnel",
        "session-execution": "execution-quality",
        "execution-edge": "execution-quality",
        "edge-search-pipeline": "relationship-factory",
        "finam-instruments": "market-prerequisites",
        "strategy-generator": "entry-analysis",
        "failure-diagnostics": "block-analysis"
    };
    let refreshInProgress = false;
    let initialRouteApplied = false;

    function applyRoute() {
        if (initialRouteApplied) return;
        initialRouteApplied = true;
        const routeCode = globalObject.location.pathname.split("/").filter(Boolean).pop();
        const sectionId = SECTION_BY_ROUTE[routeCode];
        if (!sectionId) return;
        const section = globalObject.document.getElementById(sectionId);
        if (!section) return;
        section.setAttribute("data-active-route", "true");
        section.scrollIntoView({block: "start"});
    }

    async function refresh() {
        if (refreshInProgress || globalObject.document.hidden) return;
        refreshInProgress = true;
        const scrollX = globalObject.scrollX;
        const scrollY = globalObject.scrollY;
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
            mount.setAttribute("data-last-refresh-at", new Date().toISOString());
            if (initialRouteApplied) globalObject.scrollTo(scrollX, scrollY);
            applyRoute();
        } catch (error) {
            if (mount.getAttribute("data-runtime-status") !== "READY") {
                mount.textContent = "Не удалось загрузить центр управления.";
                mount.setAttribute("data-runtime-status", "FAILED");
            }
            mount.setAttribute("data-runtime-error", String(error && error.message ? error.message : error));
        } finally {
            refreshInProgress = false;
        }
    }

    refresh();
    globalObject.setInterval(refresh, REFRESH_INTERVAL_MS);
    globalObject.document.addEventListener("visibilitychange", refresh);
})(window);
