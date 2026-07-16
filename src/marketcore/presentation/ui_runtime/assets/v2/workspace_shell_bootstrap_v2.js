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

    async function start() {
        const mountElement = globalObject.document.getElementById(ROOT_ID);
        if (!mountElement) throw new Error("WORKSPACE_SHELL_V2_MOUNT_REQUIRED");
        const services = await globalObject.MarketCoreBrowserPresentationServicesV2.load({localeCode: "ru-RU"});
        let actionSink;

        const render = async (endpoint) => globalObject.MarketCoreBrowserBootstrapV2.start({
            endpoint,
            documentObject: globalObject.document,
            mountElement,
            translate: services.translate,
            format: services.format,
            actionSink
        });

        actionSink = globalObject.MarketCoreBrowserActionControllerV2.create({
            onNavigation: async (targetId) => {
                const endpoint = ENDPOINT_BY_TARGET[targetId];
                if (!endpoint) throw new Error(`WORKSPACE_SHELL_V2_TARGET_UNKNOWN:${targetId}`);
                await render(endpoint);
            }
        });

        await render(ENDPOINT_BY_TARGET["container.home"]);
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
