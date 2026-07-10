"use strict";

(function installMarketCoreBrowserRenderTreeExecutorV1(globalObject) {
    const EXECUTOR_VERSION =
        "marketcore.browser_render_tree_executor.v1";

    const STATUS = Object.freeze({
        SUCCESS: "SUCCESS",
        FAILED: "FAILED"
    });

    class BrowserRenderTreeExecutorErrorV1 extends Error {
        constructor(code, detail) {
            super(
                detail === undefined
                    ? code
                    : `${code}:${detail}`
            );

            this.name = "BrowserRenderTreeExecutorErrorV1";
            this.code = code;
            this.detail = detail;
        }
    }

    function fail(code, detail) {
        throw new BrowserRenderTreeExecutorErrorV1(
            code,
            detail
        );
    }

    function requireValidator() {
        const validator =
            globalObject.MarketCoreRenderTreeValidatorV1;

        if (
            validator === undefined
            || validator === null
            || typeof validator.validate !== "function"
        ) {
            fail(
                "BROWSER_RENDER_TREE_VALIDATOR_REQUIRED"
            );
        }

        return validator;
    }

    function requireDriverFactory() {
        const exportedDriver =
            globalObject.MarketCoreBrowserDomDriverV1;

        if (
            exportedDriver === undefined
            || exportedDriver === null
            || typeof exportedDriver.Driver !== "function"
        ) {
            fail(
                "BROWSER_RENDER_TREE_DRIVER_REQUIRED"
            );
        }

        return exportedDriver.Driver;
    }

    function validateOptions(options) {
        if (
            options === undefined
            || options === null
            || typeof options !== "object"
        ) {
            fail(
                "BROWSER_RENDER_TREE_EXECUTOR_OPTIONS_REQUIRED"
            );
        }

        if (
            options.mountElement === undefined
            || options.mountElement === null
        ) {
            fail(
                "BROWSER_RENDER_TREE_MOUNT_ELEMENT_REQUIRED"
            );
        }

        if (
            options.documentObject === undefined
            || options.documentObject === null
        ) {
            fail(
                "BROWSER_RENDER_TREE_DOCUMENT_REQUIRED"
            );
        }
    }

    function walkNode(
        node,
        driver,
        state,
        depth,
        path
    ) {
        driver.renderNode(
            node,
            Object.freeze({
                depth,
                path
            })
        );

        state.nodesProcessed += 1;

        for (
            let index = 0;
            index < node.children.length;
            index += 1
        ) {
            walkNode(
                node.children[index],
                driver,
                state,
                depth + 1,
                `${path}.children[${index}]`
            );
        }
    }

    function executeRenderTree(payload, options) {
        validateOptions(options);

        const validator = requireValidator();
        const Driver = requireDriverFactory();

        /*
         * Валидация выполняется до создания драйвера
         * и до любых изменений целевой платформы.
         */
        const validationResult =
            validator.validate(payload);

        const driver = new Driver({
            documentObject: options.documentObject,
            mountElement: options.mountElement
        });

        const state = {
            nodesProcessed: 0
        };

        try {
            driver.beginDocument(
                payload,
                Object.freeze({
                    executorVersion: EXECUTOR_VERSION,
                    schemaVersion:
                        validationResult.schemaVersion,
                    expectedNodeCount:
                        validationResult.nodeCount
                })
            );

            walkNode(
                payload.root,
                driver,
                state,
                0,
                "root"
            );

            const driverResult = driver.endDocument(
                payload,
                Object.freeze({
                    executorVersion: EXECUTOR_VERSION,
                    nodesProcessed:
                        state.nodesProcessed
                })
            );

            return Object.freeze({
                status: STATUS.SUCCESS,
                success: true,
                nodesProcessed:
                    state.nodesProcessed,
                diagnostics: Object.freeze([]),
                driverResult
            });
        } catch (error) {
            return Object.freeze({
                status: STATUS.FAILED,
                success: false,
                nodesProcessed:
                    state.nodesProcessed,
                diagnostics: Object.freeze([
                    (
                        "BROWSER_RENDER_TREE_EXECUTION_FAILED:"
                        + `${error.name || "Error"}:`
                        + `${error.message || String(error)}`
                    )
                ]),
                driverResult: null
            });
        }
    }

    globalObject.MarketCoreBrowserRenderTreeExecutorV1 =
        Object.freeze({
            executorVersion: EXECUTOR_VERSION,
            status: STATUS,
            ExecutorError:
                BrowserRenderTreeExecutorErrorV1,
            executeRenderTree
        });
})(globalThis);
