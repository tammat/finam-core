"use strict";

(function startMarketCoreWorkspaceShellV2(globalObject) {
    const ROOT_ID = "marketcore-workspace-root";
    const ENDPOINT_BY_TARGET = Object.freeze({
        "container.home": "/api/v2/domain-render-tree/home",
        "container.capital": "/api/v2/domain-render-tree/capital",
        "container.edge": "/api/v2/domain-render-tree/control-center",
        "container.research": "/api/v2/domain-render-tree/research",
        "container.intraday": "/api/v2/domain-render-tree/intraday",
        "container.portfolio": "/api/v2/domain-render-tree/portfolio",
        "container.risk": "/api/v2/domain-render-tree/risk",
        "container.program": "/api/v2/domain-render-tree/program",
        "container.settings": "/api/v2/domain-render-tree/settings"
    });

    function initialTarget(pathname) {
        const path = String(pathname || "").toLowerCase();
        if (path.includes("/portfolio")) return "container.portfolio";
        if (path.includes("/control-center") || path.includes("/edge-oos")) return "container.edge";
        return "container.home";
    }

    async function start() {
        const mountElement = globalObject.document.getElementById(ROOT_ID);
        if (!mountElement) throw new Error("WORKSPACE_SHELL_V2_MOUNT_REQUIRED");
        const services = await globalObject.MarketCoreBrowserPresentationServicesV2.load({localeCode: "ru-RU"});
        let actionSink;
        let currentEndpoint = ENDPOINT_BY_TARGET[initialTarget(globalObject.location && globalObject.location.pathname)];

        const render = async (endpoint) => {
            currentEndpoint = endpoint;
            return globalObject.MarketCoreBrowserBootstrapV2.start({
            endpoint: currentEndpoint,
            documentObject: globalObject.document,
            mountElement,
            translate: services.translate,
            format: services.format,
            actionSink
            });
        };

        actionSink = globalObject.MarketCoreBrowserActionControllerV2.create({
            onNavigation: async (targetId) => {
                const endpoint = ENDPOINT_BY_TARGET[targetId];
                if (!endpoint) throw new Error(`WORKSPACE_SHELL_V2_TARGET_UNKNOWN:${targetId}`);
                await render(endpoint);
            },
            onCommand: async () => {
                await new Promise((resolve) => globalObject.setTimeout(resolve, 800));
                await render(currentEndpoint);
                globalObject.setTimeout(() => render(currentEndpoint), 2200);
            },
        });

        await render(currentEndpoint);
        mountElement.setAttribute("data-runtime-status", "READY");
    }

    const launch = () => start().catch((error) => {
        globalObject.console.error("MARKETCORE_WORKSPACE_SHELL_V2_FAILED", error);
        const mountElement = globalObject.document.getElementById(ROOT_ID);
        if (mountElement) mountElement.setAttribute("data-runtime-status", "FAILED");
    });
    if (globalObject.document.readyState === "loading") {
        globalObject.document.addEventListener("DOMContentLoaded", launch, {once: true});
    } else {
        launch();
    }
})(globalThis);
