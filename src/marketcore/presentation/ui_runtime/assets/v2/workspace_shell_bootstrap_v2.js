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
        if (path.includes("/research")) return "container.research";
        if (path.includes("/intraday")) return "container.intraday";
        if (path.includes("/portfolio")) return "container.portfolio";
        if (path.includes("/capital")) return "container.capital";
        if (path.includes("/risk")) return "container.risk";
        if (path.includes("/program")) return "container.program";
        if (path.includes("/settings")) return "container.settings";
        if (path.includes("/control-center") || path.includes("/edge-oos")) return "container.edge";
        return "container.home";
    }

    async function start() {
        const mountElement = globalObject.document.getElementById(ROOT_ID);
        if (!mountElement) throw new Error("WORKSPACE_SHELL_V2_MOUNT_REQUIRED");
        const backButton = globalObject.document.getElementById("marketcore-workspace-back");
        const homeButton = globalObject.document.getElementById("marketcore-workspace-home");
        const services = await globalObject.MarketCoreBrowserPresentationServicesV2.load({localeCode: "ru-RU"});
        mountElement.setAttribute("data-loading-label", services.translate("workspace.loading", {}, services.localeCode));
        let actionSink;
        const initialTargetId = initialTarget(globalObject.location && globalObject.location.pathname);
        let currentTargetId = initialTargetId;
        let currentEndpoint = ENDPOINT_BY_TARGET[currentTargetId];
        const navigationStack = [];
        let refreshInFlight = false;
        let researchRefreshTimer = null;

        const updateBackButton = () => {
            if (!backButton) return;
            const atHome = currentTargetId === "container.home" && navigationStack.length === 0;
            backButton.hidden = false;
            backButton.disabled = atHome;
            backButton.textContent = navigationStack.length > 0 ? "← Назад" : "← Главная";
            backButton.setAttribute("aria-label", atHome ? "Вы на главной странице" : backButton.textContent);
            if (homeButton) homeButton.disabled = false;
        };

        const render = async (endpoint) => {
            currentEndpoint = endpoint;
            mountElement.setAttribute("data-runtime-status", "LOADING");
            mountElement.setAttribute("aria-busy", "true");
            let result;
            try {
                result = await globalObject.MarketCoreBrowserBootstrapV2.start({
                    endpoint: currentEndpoint,
                    documentObject: globalObject.document,
                    mountElement,
                    translate: services.translate,
                    format: services.format,
                    actionSink
                });
                mountElement.setAttribute("data-runtime-status", "READY");
            } catch (error) {
                mountElement.setAttribute("data-runtime-status", "FAILED");
                mountElement.setAttribute("data-runtime-error", error && error.message ? error.message : String(error));
                throw error;
            } finally {
                mountElement.removeAttribute("aria-busy");
            }
            if (researchRefreshTimer) globalObject.clearInterval(researchRefreshTimer);
            researchRefreshTimer = currentTargetId === "container.research"
                ? globalObject.setInterval(() => {
                    if (refreshInFlight) return;
                    refreshInFlight = true;
                    render(currentEndpoint).finally(() => { refreshInFlight = false; });
                }, 10000)
                : null;
            return result;
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

        if (homeButton) homeButton.addEventListener("click", async () => {
            navigationStack.length = 0;
            currentTargetId = "container.home";
            await render(ENDPOINT_BY_TARGET[currentTargetId]);
            updateBackButton();
        });

        await render(currentEndpoint);
        updateBackButton();
        mountElement.setAttribute("data-runtime-status", "READY");
        globalObject.setInterval(async () => {
            if (refreshInFlight || globalObject.document.visibilityState !== "visible") return;
            if (!currentTargetId || !["container.edge", "container.research"].includes(currentTargetId)) return;
            if (globalObject.document.querySelector("[role='dialog']")) return;
            refreshInFlight = true;
            try { await render(currentEndpoint); }
            catch (error) { globalObject.console.error("MARKETCORE_AUTO_REFRESH_FAILED", error); }
            finally { refreshInFlight = false; }
        }, 5000);
    }

    const launch = () => start().catch((error) => {
        globalObject.console.error("MARKETCORE_WORKSPACE_SHELL_V2_FAILED", error);
        const mountElement = globalObject.document.getElementById(ROOT_ID);
        if (mountElement) {
            mountElement.setAttribute("data-runtime-status", "FAILED");
            mountElement.setAttribute("data-runtime-error", error && error.message ? error.message : String(error));
        }
    });
    if (globalObject.document.readyState === "loading") {
        globalObject.document.addEventListener("DOMContentLoaded", launch, {once: true});
    } else {
        launch();
    }
})(globalThis);
