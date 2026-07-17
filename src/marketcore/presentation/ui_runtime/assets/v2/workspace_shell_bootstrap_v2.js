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
        const backButton = globalObject.document.getElementById("marketcore-workspace-back");
        const services = await globalObject.MarketCoreBrowserPresentationServicesV2.load({localeCode: "ru-RU"});
        let actionSink;
        const initialTargetId = initialTarget(globalObject.location && globalObject.location.pathname);
        let currentTargetId = initialTargetId;
        let currentEndpoint = ENDPOINT_BY_TARGET[currentTargetId];
        const navigationStack = [];

        const updateBackButton = () => {
            if (!backButton) return;
            const atHome = currentTargetId === "container.home" && navigationStack.length === 0;
            backButton.hidden = false;
            backButton.disabled = atHome;
            backButton.textContent = navigationStack.length > 0 ? "← Назад" : "← Главная";
            backButton.setAttribute("aria-label", atHome ? "Вы на главной странице" : backButton.textContent);
        };

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
                if (targetId === currentTargetId) return;
                navigationStack.push(currentTargetId);
                currentTargetId = targetId;
                await render(endpoint);
                updateBackButton();
            },
            onCommand: async () => {
                await new Promise((resolve) => globalObject.setTimeout(resolve, 800));
                await render(currentEndpoint);
                globalObject.setTimeout(() => render(currentEndpoint), 2200);
            },
        });

        if (backButton) backButton.addEventListener("click", async () => {
            const previousTargetId = navigationStack.pop();
            if (!previousTargetId && currentTargetId === "container.home") return updateBackButton();
            currentTargetId = previousTargetId || "container.home";
            await render(ENDPOINT_BY_TARGET[currentTargetId]);
            updateBackButton();
        });

        await render(currentEndpoint);
        updateBackButton();
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
