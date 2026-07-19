"use strict";

(function installMarketCoreBrowserBootstrapV2(globalObject) {
    const BOOTSTRAP_VERSION = "marketcore.browser_bootstrap.v2";
    const MEDIA_TYPE = "application/vnd.marketcore.render-tree+json";

    class BrowserBootstrapErrorV2 extends Error {
        constructor(code, detail) {
            super(detail === undefined ? code : `${code}:${detail}`);
            this.name = "BrowserBootstrapErrorV2";
            this.code = code;
        }
    }

    function fail(code, detail) { throw new BrowserBootstrapErrorV2(code, detail); }

    async function start(options) {
        if (!options || typeof options !== "object") fail("BROWSER_BOOTSTRAP_V2_OPTIONS_REQUIRED");
        if (!options.mountElement) fail("BROWSER_BOOTSTRAP_V2_MOUNT_REQUIRED");
        if (!options.documentObject) fail("BROWSER_BOOTSTRAP_V2_DOCUMENT_REQUIRED");
        if (typeof options.translate !== "function") fail("BROWSER_BOOTSTRAP_V2_TRANSLATOR_REQUIRED");
        if (typeof options.format !== "function") fail("BROWSER_BOOTSTRAP_V2_FORMATTER_REQUIRED");
        if (typeof globalObject.fetch !== "function") fail("BROWSER_BOOTSTRAP_V2_FETCH_REQUIRED");

        const endpoint = options.endpoint || "/api/v2/domain-render-tree/home";
        const response = await globalObject.fetch(endpoint, {
            method: "GET",
            headers: {Accept: MEDIA_TYPE},
            credentials: "same-origin",
            cache: "no-store"
        });
        if (!response.ok) fail("BROWSER_BOOTSTRAP_V2_HTTP_FAILED", String(response.status));
        const contentType = response.headers.get("content-type") || "";
        if (!contentType.toLowerCase().startsWith(MEDIA_TYPE)) {
            fail("BROWSER_BOOTSTRAP_V2_CONTENT_TYPE_INVALID", contentType);
        }

        const runtime = globalObject.MarketCoreDomainRenderTreeRuntimeV2;
        const validator = globalObject.MarketCoreRenderTreeValidatorV2;
        const exportedDriver = globalObject.MarketCoreBrowserPlatformDriverV2;
        if (!runtime || typeof runtime.execute !== "function") fail("BROWSER_BOOTSTRAP_V2_RUNTIME_REQUIRED");
        if (!validator || typeof validator.validate !== "function") fail("BROWSER_BOOTSTRAP_V2_VALIDATOR_REQUIRED");
        if (!exportedDriver || typeof exportedDriver.Driver !== "function") fail("BROWSER_BOOTSTRAP_V2_DRIVER_REQUIRED");

        const payload = await response.json();
        const stagingElement = options.documentObject.createElement("div");
        const driver = new exportedDriver.Driver({
            documentObject: options.documentObject,
            mountElement: stagingElement,
            actionSink: options.actionSink
        });
        const result = runtime.execute(payload, {
            validator,
            driver,
            translate: options.translate,
            format: options.format
        });
        options.mountElement.replaceChildren(...stagingElement.childNodes);
        return result;
    }

    globalObject.MarketCoreBrowserBootstrapV2 = Object.freeze({
        bootstrapVersion: BOOTSTRAP_VERSION,
        mediaType: MEDIA_TYPE,
        BootstrapError: BrowserBootstrapErrorV2,
        start
    });
})(globalThis);
