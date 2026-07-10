"use strict";

(function installMarketCoreHomeRuntimeSwitchV1(globalObject) {
    const SWITCH_VERSION =
        "marketcore.home_render_tree_runtime_switch.v1";

    const HOME_ENDPOINT =
        "/api/v1/render-tree/home";

    const ROOT_ELEMENT_ID =
        "marketcore-home-runtime-root";

    class HomeRuntimeSwitchErrorV1 extends Error {
        constructor(code, detail) {
            super(
                detail === undefined
                    ? code
                    : `${code}:${detail}`
            );

            this.name = "HomeRuntimeSwitchErrorV1";
            this.code = code;
            this.detail = detail;
        }
    }

    function fail(code, detail) {
        throw new HomeRuntimeSwitchErrorV1(
            code,
            detail
        );
    }

    function requireDocument() {
        const documentObject = globalObject.document;

        if (
            documentObject === undefined
            || documentObject === null
            || typeof documentObject.getElementById
                !== "function"
        ) {
            fail("HOME_RUNTIME_DOCUMENT_REQUIRED");
        }

        return documentObject;
    }

    function requireExecutor() {
        const executor =
            globalObject
                .MarketCoreBrowserRenderTreeExecutorV1;

        if (
            executor === undefined
            || executor === null
            || typeof executor.executeRenderTree
                !== "function"
        ) {
            fail("HOME_RUNTIME_EXECUTOR_REQUIRED");
        }

        return executor;
    }

    function requireMountElement(documentObject) {
        const mountElement =
            documentObject.getElementById(
                ROOT_ELEMENT_ID
            );

        if (mountElement === null) {
            fail("HOME_RUNTIME_MOUNT_ELEMENT_REQUIRED");
        }

        return mountElement;
    }

    async function loadPayload() {
        if (typeof globalObject.fetch !== "function") {
            fail("HOME_RUNTIME_FETCH_REQUIRED");
        }

        const response = await globalObject.fetch(
            HOME_ENDPOINT,
            {
                method: "GET",
                headers: {
                    Accept: "application/json"
                },
                credentials: "same-origin",
                cache: "no-store"
            }
        );

        if (!response.ok) {
            fail(
                "HOME_RUNTIME_HTTP_FAILED",
                String(response.status)
            );
        }

        const contentType =
            response.headers.get("content-type") || "";

        if (
            !contentType
                .toLowerCase()
                .startsWith("application/json")
        ) {
            fail(
                "HOME_RUNTIME_CONTENT_TYPE_INVALID",
                contentType
            );
        }

        return response.json();
    }

    function showFailure(mountElement, error) {
        mountElement.replaceChildren();

        const message =
            mountElement.ownerDocument
                .createElement("div");

        message.setAttribute(
            "role",
            "alert"
        );
        message.setAttribute(
            "data-runtime-error",
            "HOME_RENDER_FAILED"
        );
        message.textContent =
            "Не удалось загрузить рабочий стол.";

        mountElement.appendChild(message);
        mountElement.setAttribute(
            "data-runtime-status",
            "FAILED"
        );
        mountElement.setAttribute(
            "data-runtime-error-code",
            String(
                error && error.code
                    ? error.code
                    : "UNKNOWN"
            )
        );
    }

    async function start() {
        const documentObject = requireDocument();
        const mountElement =
            requireMountElement(documentObject);
        const executor = requireExecutor();

        mountElement.setAttribute(
            "data-runtime-status",
            "LOADING"
        );

        try {
            const payload = await loadPayload();

            const result = executor.executeRenderTree(
                payload,
                {
                    documentObject,
                    mountElement
                }
            );

            if (!result.success) {
                fail(
                    "HOME_RUNTIME_EXECUTION_FAILED",
                    result.diagnostics.join("|")
                );
            }

            mountElement.setAttribute(
                "data-runtime-status",
                "READY"
            );
            mountElement.setAttribute(
                "data-runtime-version",
                SWITCH_VERSION
            );
            mountElement.setAttribute(
                "data-runtime-nodes",
                String(result.nodesProcessed)
            );

            return result;
        } catch (error) {
            showFailure(mountElement, error);
            throw error;
        }
    }

    globalObject.MarketCoreHomeRuntimeSwitchV1 =
        Object.freeze({
            switchVersion: SWITCH_VERSION,
            endpoint: HOME_ENDPOINT,
            rootElementId: ROOT_ELEMENT_ID,
            start
        });

    if (
        globalObject.document
        && globalObject.document.readyState
            === "loading"
    ) {
        globalObject.document.addEventListener(
            "DOMContentLoaded",
            () => {
                start().catch((error) => {
                    globalObject.console.error(
                        "MARKETCORE_HOME_RUNTIME_FAILED",
                        error
                    );
                });
            },
            {
                once: true
            }
        );
    } else {
        start().catch((error) => {
            globalObject.console.error(
                "MARKETCORE_HOME_RUNTIME_FAILED",
                error
            );
        });
    }
})(globalThis);
