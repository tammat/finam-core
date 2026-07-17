"use strict";

(function installMarketCoreDomainRenderTreeRuntimeV2(globalObject) {
    const RUNTIME_VERSION = "marketcore.domain_render_tree_runtime.v2";

    class DomainRenderTreeRuntimeErrorV2 extends Error {
        constructor(code, detail) {
            super(detail === undefined ? code : `${code}:${detail}`);
            this.name = "DomainRenderTreeRuntimeErrorV2";
            this.code = code;
        }
    }

    function fail(code, detail) { throw new DomainRenderTreeRuntimeErrorV2(code, detail); }

    function requireFunction(value, code) {
        if (typeof value !== "function") fail(code);
        return value;
    }

    function execute(documentPayload, options) {
        if (!options || typeof options !== "object") fail("RUNTIME_V2_OPTIONS_REQUIRED");
        const validator = options.validator;
        if (!validator || typeof validator.validate !== "function") fail("RUNTIME_V2_VALIDATOR_REQUIRED");
        const driver = options.driver;
        if (!driver || typeof driver !== "object") fail("RUNTIME_V2_DRIVER_REQUIRED");
        const translate = requireFunction(options.translate, "RUNTIME_V2_TRANSLATOR_REQUIRED");
        const format = requireFunction(options.format, "RUNTIME_V2_FORMATTER_REQUIRED");
        for (const method of ["beginDocument", "renderNode", "endDocument"]) {
            requireFunction(driver[method], `RUNTIME_V2_DRIVER_METHOD_REQUIRED:${method}`);
        }

        const validation = validator.validate(documentPayload);
        let nodesProcessed = 0;
        driver.beginDocument(documentPayload, Object.freeze({runtimeVersion: RUNTIME_VERSION}));

        function visit(node, depth, path) {
            const content = node.content || null;
            let displayValue = null;
            let tooltipValue = null;
            if (content !== null) {
                if (content.message_key !== undefined) {
                    displayValue = translate(
                        content.message_key,
                        Object.freeze({...content.message_args || {}}),
                        documentPayload.locale_code,
                        documentPayload.fallback_locale_code
                    );
                    if (content.message_args && content.message_args.tooltip_key) {
                        tooltipValue = translate(
                            content.message_args.tooltip_key,
                            Object.freeze({}),
                            documentPayload.locale_code,
                            documentPayload.fallback_locale_code
                        );
                    }
                } else {
                    displayValue = format(
                        content.value,
                        content.format_code || null,
                        documentPayload.locale_code,
                        documentPayload.timezone_code
                    );
                }
            }
            driver.renderNode(node, Object.freeze({depth, path, displayValue, tooltipValue}));
            nodesProcessed += 1;
            node.children.forEach((child, index) => visit(child, depth + 1, `${path}.children[${index}]`));
        }

        visit(documentPayload.root, 0, "root");
        const driverResult = driver.endDocument(documentPayload, Object.freeze({nodesProcessed}));
        return Object.freeze({success: true, nodesProcessed, schemaVersion: validation.schemaVersion, driverResult});
    }

    globalObject.MarketCoreDomainRenderTreeRuntimeV2 = Object.freeze({
        runtimeVersion: RUNTIME_VERSION,
        RuntimeError: DomainRenderTreeRuntimeErrorV2,
        execute
    });
})(globalThis);
