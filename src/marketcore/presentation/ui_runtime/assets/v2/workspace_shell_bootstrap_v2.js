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
    const ROUTE_BY_TARGET = Object.freeze({
        "container.home": "/workspace-v2",
        "container.capital": "/workspace-v2/capital",
        "container.edge": "/workspace-v2/control-center/edge-oos",
        "container.research": "/workspace-v2/research",
        "container.intraday": "/workspace-v2/intraday",
        "container.portfolio": "/workspace-v2/portfolio",
        "container.risk": "/workspace-v2/risk",
        "container.program": "/workspace-v2/program",
        "container.settings": "/workspace-v2/settings"
    });
    const OPERATOR_MENU_ITEMS = Object.freeze([
        ["container.home", "workspace.menu.home"],
        ["container.research", "workspace.menu.research"],
        ["container.edge", "workspace.menu.control"],
        ["container.intraday", "workspace.menu.intraday"],
        ["container.portfolio", "workspace.menu.portfolio"],
        ["container.risk", "workspace.menu.risk"],
        ["container.capital", "workspace.menu.capital"],
        ["container.program", "workspace.menu.system"],
        ["container.settings", "workspace.menu.settings"]
    ]);

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

        const panelStateStorageKey = () => `marketcore.workspace-v2.state:${currentTargetId}`;

        const stableElementKey = (element) => {
            if (!element || !element.getAttribute) return null;
            const nodeId = element.getAttribute("data-mc-node-id");
            if (nodeId) return `node:${nodeId}`;
            const sectionGroup = element.getAttribute("data-mc-section-group");
            if (sectionGroup) return `group:${sectionGroup}`;
            if (element.id) return `id:${element.id}`;
            return null;
        };

        const findStableElement = (key) => {
            if (!key) return null;
            const candidates = mountElement.querySelectorAll(
                "[data-mc-node-id], [data-mc-section-group], [id]"
            );
            return Array.from(candidates).find((element) => stableElementKey(element) === key) || null;
        };

        const capturePanelState = () => {
            const elements = {};
            mountElement.querySelectorAll("[data-mc-node-id], details[data-mc-section-group], [id]")
                .forEach((element) => {
                    const key = stableElementKey(element);
                    if (!key) return;
                    const state = {};
                    if (element.tagName === "DETAILS") state.open = Boolean(element.open);
                    if (element.hasAttribute("aria-expanded")) {
                        state.ariaExpanded = element.getAttribute("aria-expanded");
                    }
                    if (element.hasAttribute("aria-pressed")) {
                        state.ariaPressed = element.getAttribute("aria-pressed");
                    }
                    if (element.getAttribute("data-mc-selected") === "true") state.selected = true;
                    if (element.scrollTop || element.scrollLeft) {
                        state.scrollTop = element.scrollTop;
                        state.scrollLeft = element.scrollLeft;
                    }
                    if (Object.keys(state).length) elements[key] = state;
                });
            const scoutFilters = Array.from(mountElement.querySelectorAll("table[data-mc-scout-filter]"))
                .map((table) => ({key: stableElementKey(table), filter: table.dataset.mcScoutFilter}))
                .filter((item) => item.key && item.filter);
            const activeElement = globalObject.document.activeElement;
            return {
                scrollX: globalObject.scrollX || 0,
                scrollY: globalObject.scrollY || 0,
                mountScrollTop: mountElement.scrollTop || 0,
                mountScrollLeft: mountElement.scrollLeft || 0,
                focused: mountElement.contains(activeElement) ? stableElementKey(activeElement) : null,
                elements,
                scoutFilters
            };
        };

        const persistPanelState = (state = capturePanelState()) => {
            try { globalObject.sessionStorage.setItem(panelStateStorageKey(), JSON.stringify(state)); }
            catch (error) { globalObject.console.warn("MARKETCORE_PANEL_STATE_SAVE_FAILED", error); }
            return state;
        };

        const storedPanelState = () => {
            try {
                const raw = globalObject.sessionStorage.getItem(panelStateStorageKey());
                return raw ? JSON.parse(raw) : null;
            } catch (error) {
                globalObject.console.warn("MARKETCORE_PANEL_STATE_LOAD_FAILED", error);
                return null;
            }
        };

        const restorePanelState = (state, options = {}) => {
            if (!state) return;
            const restorePageScroll = options.restorePageScroll !== false;
            Object.entries(state.elements || {}).forEach(([key, value]) => {
                const element = findStableElement(key);
                if (!element) return;
                if (element.tagName === "DETAILS" && typeof value.open === "boolean") element.open = value.open;
                if (value.ariaExpanded != null) element.setAttribute("aria-expanded", value.ariaExpanded);
                if (value.ariaPressed != null) element.setAttribute("aria-pressed", value.ariaPressed);
                if (value.selected) element.setAttribute("data-mc-selected", "true");
                if (Number.isFinite(value.scrollTop)) element.scrollTop = value.scrollTop;
                if (Number.isFinite(value.scrollLeft)) element.scrollLeft = value.scrollLeft;
            });
            (state.scoutFilters || []).forEach(({key, filter}) => {
                const table = findStableElement(key);
                const toolbar = table && table.previousElementSibling;
                const button = toolbar && Array.from(toolbar.querySelectorAll("button[data-filter]"))
                    .find((candidate) => candidate.dataset.filter === filter);
                if (button) button.click();
            });
            mountElement.scrollTop = state.mountScrollTop || 0;
            mountElement.scrollLeft = state.mountScrollLeft || 0;
            const focused = findStableElement(state.focused);
            if (focused && typeof focused.focus === "function") focused.focus({preventScroll: true});
            globalObject.scrollTo(
                restorePageScroll ? (state.scrollX || 0) : 0,
                restorePageScroll ? (state.scrollY || 0) : 0
            );
        };

        const syncRoute = (targetId, replace = false) => {
            const route = ROUTE_BY_TARGET[targetId];
            if (!route || !globalObject.history || globalObject.location.pathname === route) return;
            const method = replace ? "replaceState" : "pushState";
            globalObject.history[method]({marketcoreTargetId: targetId}, "", route);
        };

        const updateBackButton = () => {
            if (!backButton) return;
            const atHome = currentTargetId === "container.home" && navigationStack.length === 0;
            backButton.hidden = false;
            backButton.disabled = atHome;
            backButton.textContent = navigationStack.length > 0 ? "← Назад" : "← Главная";
            backButton.setAttribute("aria-label", atHome ? "Вы на главной странице" : backButton.textContent);
            if (homeButton) homeButton.disabled = false;
        };

        const navigateToTarget = async (targetId) => {
            const endpoint = ENDPOINT_BY_TARGET[targetId];
            if (!endpoint) throw new Error(`WORKSPACE_SHELL_V2_TARGET_UNKNOWN:${targetId}`);
            if (targetId === currentTargetId) return;
            persistPanelState();
            navigationStack.push(currentTargetId);
            currentTargetId = targetId;
            await render(endpoint, {restoreStored: true});
            syncRoute(targetId);
            updateBackButton();
        };

        const installControlDrawer = () => {
            const existing = globalObject.document.getElementById("marketcore-control-drawer");
            if (existing) existing.remove();
            const drawer = globalObject.document.createElement("aside");
            drawer.id = "marketcore-control-drawer";
            drawer.setAttribute("aria-label", services.translate("workspace.drawer.title", {}, services.localeCode));
            const collapsedKey = "marketcore.workspace-v2.drawer-collapsed";
            let collapsed = globalObject.matchMedia("(max-width: 900px)").matches;
            try {
                const stored = globalObject.sessionStorage.getItem(collapsedKey);
                if (stored !== null) collapsed = stored === "true";
            }
            catch (error) { globalObject.console.warn("MARKETCORE_DRAWER_STATE_LOAD_FAILED", error); }
            drawer.dataset.collapsed = String(collapsed);

            const header = globalObject.document.createElement("header");
            const brand = globalObject.document.createElement("div");
            brand.className = "mc-control-drawer-brand";
            const brandMark = globalObject.document.createElement("span");
            brandMark.className = "mc-control-drawer-brand-mark";
            brandMark.textContent = "M";
            const title = globalObject.document.createElement("strong");
            title.textContent = services.translate("workspace.drawer.brand", {}, services.localeCode);
            brand.append(brandMark, title);
            const toggle = globalObject.document.createElement("button");
            toggle.type = "button";
            toggle.className = "mc-control-drawer-toggle";
            const syncToggle = () => {
                const isCollapsed = drawer.dataset.collapsed === "true";
                toggle.textContent = isCollapsed ? "☰" : "×";
                toggle.title = services.translate(
                    isCollapsed ? "workspace.drawer.open" : "workspace.drawer.close",
                    {}, services.localeCode
                );
                toggle.setAttribute("aria-expanded", String(!isCollapsed));
                globalObject.document.body.dataset.mcDrawerOpen = String(!isCollapsed);
            };
            toggle.addEventListener("click", () => {
                drawer.dataset.collapsed = String(drawer.dataset.collapsed !== "true");
                try { globalObject.sessionStorage.setItem(collapsedKey, drawer.dataset.collapsed); }
                catch (error) { globalObject.console.warn("MARKETCORE_DRAWER_STATE_SAVE_FAILED", error); }
                syncToggle();
            });
            header.append(brand, toggle);

            const content = globalObject.document.createElement("div");
            content.className = "mc-control-drawer-content";
            const nav = globalObject.document.createElement("div");
            nav.className = "mc-control-drawer-navigation";
            const addNav = (labelKey, sourceButton) => {
                const button = globalObject.document.createElement("button");
                button.type = "button";
                button.textContent = services.translate(labelKey, {}, services.localeCode);
                button.addEventListener("click", () => sourceButton && sourceButton.click());
                nav.appendChild(button);
            };
            addNav("workspace.drawer.back", backButton);
            addNav("workspace.drawer.home", homeButton);
            content.appendChild(nav);

            const functions = globalObject.document.createElement("div");
            functions.className = "mc-control-drawer-functions";
            const functionsTitle = globalObject.document.createElement("strong");
            functionsTitle.className = "mc-control-drawer-label";
            functionsTitle.textContent = services.translate("workspace.drawer.functions", {}, services.localeCode);
            functions.appendChild(functionsTitle);
            OPERATOR_MENU_ITEMS.forEach(([targetId, labelKey]) => {
                const button = globalObject.document.createElement("button");
                button.type = "button";
                button.dataset.active = String(targetId === currentTargetId);
                button.textContent = services.translate(labelKey, {}, services.localeCode);
                button.addEventListener("click", () => {
                    if (targetId === currentTargetId) {
                        globalObject.scrollTo({top: 0, behavior: "smooth"});
                        return;
                    }
                    navigateToTarget(targetId).catch((error) =>
                        globalObject.console.error("WORKSPACE_MENU_NAVIGATION_FAILED", error));
                });
                functions.appendChild(button);
            });
            content.appendChild(functions);

            const toolbar = mountElement.querySelector(".mc-control-view-toolbar");
            if (toolbar) {
                const views = globalObject.document.createElement("div");
                views.className = "mc-control-drawer-views";
                const viewsTitle = globalObject.document.createElement("strong");
                viewsTitle.className = "mc-control-drawer-label";
                viewsTitle.textContent = services.translate("workspace.drawer.views", {}, services.localeCode);
                views.appendChild(viewsTitle);
                toolbar.querySelectorAll("button[data-mc-control-view]").forEach((source) => {
                    const button = globalObject.document.createElement("button");
                    button.type = "button";
                    button.textContent = source.textContent;
                    button.dataset.active = String(source.getAttribute("aria-pressed") === "true");
                    button.addEventListener("click", () => {
                        source.click();
                        views.querySelectorAll("button").forEach((item) => item.dataset.active = "false");
                        button.dataset.active = "true";
                    });
                    views.appendChild(button);
                });
                content.appendChild(views);
            }

            const groupList = globalObject.document.createElement("div");
            groupList.className = "mc-control-drawer-groups";
            const groupsTitle = globalObject.document.createElement("strong");
            groupsTitle.className = "mc-control-drawer-label";
            groupsTitle.textContent = services.translate("workspace.drawer.sections", {}, services.localeCode);
            groupList.appendChild(groupsTitle);
            const groups = Array.from(mountElement.querySelectorAll("details[data-mc-section-group]"))
                .map((details) => {
                    const blocked = details.querySelectorAll('[data-mc-status="BLOCKED"], [data-mc-status="FAIL"]').length;
                    const warning = details.querySelectorAll('[data-mc-status="WARNING"], [data-mc-status="REVIEW_REQUIRED"]').length;
                    const success = details.querySelectorAll(
                        '[data-mc-status="PASS"], [data-mc-status="VERIFIED"], [data-mc-status="OOS_PASS"]'
                    ).length;
                    return {details, blocked, warning, success};
                })
                .sort((left, right) => (right.blocked - left.blocked)
                    || (right.warning - left.warning)
                    || (right.success - left.success));
            groups.forEach(({details, blocked, warning, success}) => {
                const button = globalObject.document.createElement("button");
                button.type = "button";
                button.dataset.severity = blocked > 0 ? "BLOCKED"
                    : warning > 0 ? "WARNING"
                        : success > 0 ? "SUCCESS" : "NEUTRAL";
                const label = details.querySelector(".mc-control-group-heading strong")?.textContent
                    || details.dataset.mcSectionGroup;
                const count = blocked || warning || success;
                const marker = success > 0 && blocked === 0 && warning === 0 ? "+" : "";
                button.textContent = count > 0 ? `${label} · ${marker}${count}` : label;
                button.addEventListener("click", () => {
                    details.open = true;
                    groupList.querySelectorAll("button").forEach((item) => item.dataset.active = "false");
                    button.dataset.active = "true";
                    details.scrollIntoView({behavior: "smooth", block: "start"});
                });
                groupList.appendChild(button);
            });
            if (groups.length) content.appendChild(groupList);

            const opportunities = Array.from(mountElement.querySelectorAll(
                '[data-mc-status="PASS"], [data-mc-status="VERIFIED"], [data-mc-status="OOS_PASS"]'
            )).filter((element) => !element.closest("details[data-mc-section-group]")).slice(0, 5);
            if (opportunities.length) {
                const opportunityList = globalObject.document.createElement("div");
                opportunityList.className = "mc-control-drawer-opportunities";
                const heading = globalObject.document.createElement("strong");
                heading.textContent = services.translate("workspace.drawer.opportunities", {}, services.localeCode);
                opportunityList.appendChild(heading);
                opportunities.forEach((element) => {
                    const button = globalObject.document.createElement("button");
                    button.type = "button";
                    button.textContent = element.textContent.trim().slice(0, 80)
                        || services.translate("workspace.drawer.confirmed", {}, services.localeCode);
                    button.addEventListener("click", () => element.scrollIntoView({behavior: "smooth", block: "center"}));
                    opportunityList.appendChild(button);
                });
                content.insertBefore(opportunityList, groupList);
            }
            drawer.append(header, content);
            globalObject.document.body.appendChild(drawer);
            syncToggle();
        };

        const render = async (endpoint, options = {}) => {
            const panelState = options.preserveState
                ? persistPanelState()
                : (options.restoreStored ? storedPanelState() : null);
            const backgroundRefresh = Boolean(options.preserveState && mountElement.childElementCount);
            currentEndpoint = endpoint;
            if (!backgroundRefresh) {
                mountElement.setAttribute("data-runtime-status", "LOADING");
                mountElement.setAttribute("aria-busy", "true");
            }
            let result;
            try {
                result = await globalObject.MarketCoreBrowserBootstrapV2.start({
                    endpoint: currentEndpoint,
                    documentObject: globalObject.document,
                    mountElement,
                    translate: services.translate,
                    localeCode: services.localeCode,
                    format: services.format,
                    actionSink
                });
                mountElement.setAttribute("data-runtime-status", "READY");
                const stateToRestore = options.preserveState
                    ? (storedPanelState() || panelState)
                    : panelState;
                if (stateToRestore) {
                    restorePanelState(stateToRestore, {
                        restorePageScroll: options.restorePageScroll !== false
                    });
                    globalObject.requestAnimationFrame(() => globalObject.requestAnimationFrame(() => {
                        restorePanelState(stateToRestore, {
                            restorePageScroll: options.restorePageScroll !== false
                        });
                    }));
                }
                installControlDrawer();
            } catch (error) {
                mountElement.setAttribute("data-runtime-status", "FAILED");
                mountElement.setAttribute("data-runtime-error", error && error.message ? error.message : String(error));
                throw error;
            } finally {
                if (!backgroundRefresh) mountElement.removeAttribute("aria-busy");
            }
            return result;
        };

        actionSink = globalObject.MarketCoreBrowserActionControllerV2.create({
            onNavigation: navigateToTarget,
            onCommand: async () => {
                await new Promise((resolve) => globalObject.setTimeout(resolve, 800));
                await render(currentEndpoint, {preserveState: true});
                globalObject.setTimeout(() => render(currentEndpoint, {preserveState: true}), 2200);
            },
        });

        if (backButton) backButton.addEventListener("click", async () => {
            const previousTargetId = navigationStack.pop();
            if (!previousTargetId && currentTargetId === "container.home") return updateBackButton();
            persistPanelState();
            currentTargetId = previousTargetId || "container.home";
            await render(ENDPOINT_BY_TARGET[currentTargetId], {restoreStored: true});
            syncRoute(currentTargetId);
            updateBackButton();
        });

        if (homeButton) homeButton.addEventListener("click", async () => {
            persistPanelState();
            navigationStack.length = 0;
            currentTargetId = "container.home";
            await render(ENDPOINT_BY_TARGET[currentTargetId], {restoreStored: true});
            syncRoute(currentTargetId);
            updateBackButton();
        });

        globalObject.addEventListener("popstate", async () => {
            const targetId = initialTarget(globalObject.location.pathname);
            if (targetId === currentTargetId) return;
            persistPanelState();
            navigationStack.length = 0;
            currentTargetId = targetId;
            await render(ENDPOINT_BY_TARGET[currentTargetId], {restoreStored: true});
            updateBackButton();
        });

        globalObject.addEventListener("pagehide", () => persistPanelState());
        mountElement.addEventListener("toggle", (event) => {
            if (event.target && event.target.matches("details[data-mc-section-group]")) {
                persistPanelState();
            }
        }, true);

        if (globalObject.history && "scrollRestoration" in globalObject.history) {
            globalObject.history.scrollRestoration = "manual";
        }
        await render(currentEndpoint, {restoreStored: true});
        syncRoute(currentTargetId, true);
        updateBackButton();
        mountElement.setAttribute("data-runtime-status", "READY");
        globalObject.setInterval(async () => {
            if (refreshInFlight || globalObject.document.visibilityState !== "visible") return;
            if (!currentTargetId || !["container.edge", "container.research"].includes(currentTargetId)) return;
            if (globalObject.document.querySelector("[role='dialog']")) return;
            refreshInFlight = true;
            try { await render(currentEndpoint, {preserveState: true}); }
            catch (error) { globalObject.console.error("MARKETCORE_AUTO_REFRESH_FAILED", error); }
            finally { refreshInFlight = false; }
        }, 15000);
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
