"use strict";

(function installMarketCoreBrowserDomDriverV1(globalObject) {
    const DRIVER_VERSION = "marketcore.browser_dom_driver.v1";

    const TAG_BY_NODE_TYPE = Object.freeze({
        workspace: "main",
        page: "section",
        header: "header",
        section: "section",
        grid: "div",
        card: "article",
        table: "table",
        table_head: "thead",
        table_body: "tbody",
        table_row: "tr",
        table_header_cell: "th",
        table_cell: "td",
        subtitle: "p",
        text: "div",
        metric_list: "dl",
        metric_row: "div",
        metric_label: "dt",
        metric_value: "dd",
        action: "a",
        badge: "span"
    });

    const ALLOWED_ATTRIBUTES = Object.freeze({
        class: "class",
        style: "style",
        role: "role",
        aria_label: "aria-label",
        id: "id",
        href: "href",
        target: "target",
        disabled: "aria-disabled",
        "data-section": "data-section",
        "data-card": "data-card",
        "data-status": "data-status",
        "data-availability": "data-availability",
        "data-field": "data-field",
        activation_target: "data-activation-target",
        tab_index: "tabindex"
    });

    class BrowserDomDriverErrorV1 extends Error {
        constructor(code, detail) {
            super(
                detail === undefined
                    ? code
                    : `${code}:${detail}`
            );

            this.name = "BrowserDomDriverErrorV1";
            this.code = code;
            this.detail = detail;
        }
    }

    function fail(code, detail) {
        throw new BrowserDomDriverErrorV1(code, detail);
    }

    function requireDomDocument(documentObject) {
        if (
            documentObject === null
            || typeof documentObject !== "object"
            || typeof documentObject.createElement !== "function"
        ) {
            fail("BROWSER_DOM_DOCUMENT_REQUIRED");
        }
    }

    function requireMountElement(mountElement) {
        if (
            mountElement === null
            || typeof mountElement !== "object"
            || typeof mountElement.appendChild !== "function"
        ) {
            fail("BROWSER_DOM_MOUNT_ELEMENT_REQUIRED");
        }
    }

    function resolveTag(node) {
        if (node.type === "card" && node.props?.href) {
            return "a";
        }

        if (node.type === "title") {
            const level = node.props.level;

            if (![1, 2, 3].includes(level)) {
                fail(
                    "BROWSER_DOM_TITLE_LEVEL_INVALID",
                    String(level)
                );
            }

            return `h${level}`;
        }

        const tag = TAG_BY_NODE_TYPE[node.type];

        if (tag === undefined) {
            fail(
                "BROWSER_DOM_NODE_TYPE_UNSUPPORTED",
                String(node.type)
            );
        }

        return tag;
    }

    function applyProps(element, props) {
        for (const [propName, propValue] of Object.entries(props)) {
            if (propName === "level") {
                continue;
            }

            if (
                propName === "action_code"
                || propName === "status"
            ) {
                element.setAttribute(
                    `data-${propName.replaceAll("_", "-")}`,
                    String(propValue)
                );
                continue;
            }

            const attributeName = ALLOWED_ATTRIBUTES[propName];

            if (attributeName === undefined) {
                fail(
                    "BROWSER_DOM_PROP_UNSUPPORTED",
                    propName
                );
            }

            if (
                propName === "disabled"
                && propValue === false
            ) {
                continue;
            }

            element.setAttribute(
                attributeName,
                String(propValue)
            );
        }
    }

    class MarketCoreBrowserDomDriverV1 {
        constructor(options) {
            if (
                options === null
                || typeof options !== "object"
            ) {
                fail("BROWSER_DOM_DRIVER_OPTIONS_REQUIRED");
            }

            requireDomDocument(options.documentObject);
            requireMountElement(options.mountElement);

            this.documentObject = options.documentObject;
            this.mountElement = options.mountElement;
            this.elementStack = [];
            this.rootElement = null;
            this.nodesRendered = 0;
            this.started = false;
            this.completed = false;
        }

        beginDocument(payload, context) {
            if (this.started) {
                fail("BROWSER_DOM_DOCUMENT_ALREADY_STARTED");
            }

            if (
                payload === null
                || typeof payload !== "object"
                || payload.root === undefined
            ) {
                fail("BROWSER_DOM_RENDER_TREE_REQUIRED");
            }

            if (
                context === null
                || typeof context !== "object"
            ) {
                fail("BROWSER_DOM_CONTEXT_REQUIRED");
            }

            if (
                typeof this.mountElement.replaceChildren
                === "function"
            ) {
                this.mountElement.replaceChildren();
            } else {
                while (this.mountElement.firstChild) {
                    this.mountElement.removeChild(
                        this.mountElement.firstChild
                    );
                }
            }

            this.elementStack = [];
            this.rootElement = null;
            this.nodesRendered = 0;
            this.started = true;
            this.completed = false;
        }

        renderNode(node, context) {
            if (!this.started || this.completed) {
                fail("BROWSER_DOM_DOCUMENT_NOT_ACTIVE");
            }

            if (
                node === null
                || typeof node !== "object"
            ) {
                fail("BROWSER_DOM_NODE_REQUIRED");
            }

            if (
                context === null
                || typeof context !== "object"
                || !Number.isInteger(context.depth)
                || context.depth < 0
            ) {
                fail("BROWSER_DOM_NODE_DEPTH_INVALID");
            }

            const tag = resolveTag(node);
            const element = this.documentObject.createElement(tag);

            applyProps(element, node.props || {});

            if (node.type === "table_row" && node.props?.activation_target) {
                const activationTarget = String(node.props.activation_target);
                const navigate = () => globalObject.location.assign(activationTarget);
                element.addEventListener("dblclick", navigate);
                element.addEventListener("keydown", (event) => {
                    if (event.key === "Enter") {
                        event.preventDefault();
                        navigate();
                    }
                });
            }

            if (node.text) {
                element.textContent = node.text;
            }

            const depth = context.depth;

            if (depth === 0) {
                if (this.rootElement !== null) {
                    fail("BROWSER_DOM_MULTIPLE_ROOTS");
                }

                this.mountElement.appendChild(element);
                this.rootElement = element;
            } else {
                const parentElement = this.elementStack[depth - 1];

                if (parentElement === undefined) {
                    fail(
                        "BROWSER_DOM_PARENT_NOT_FOUND",
                        String(depth)
                    );
                }

                parentElement.appendChild(element);
            }

            this.elementStack[depth] = element;
            this.elementStack.length = depth + 1;
            this.nodesRendered += 1;
        }

        endDocument(payload, context) {
            if (!this.started || this.completed) {
                fail("BROWSER_DOM_DOCUMENT_NOT_ACTIVE");
            }

            if (this.rootElement === null) {
                fail("BROWSER_DOM_ROOT_NOT_RENDERED");
            }

            if (
                context === null
                || typeof context !== "object"
                || context.nodesProcessed !== this.nodesRendered
            ) {
                fail(
                    "BROWSER_DOM_NODE_COUNT_MISMATCH",
                    (
                        `${context?.nodesProcessed}`
                        + `:${this.nodesRendered}`
                    )
                );
            }

            this.completed = true;

            return Object.freeze({
                driverVersion: DRIVER_VERSION,
                nodesRendered: this.nodesRendered,
                rootElement: this.rootElement
            });
        }
    }

    globalObject.MarketCoreBrowserDomDriverV1 = Object.freeze({
        driverVersion: DRIVER_VERSION,
        Driver: MarketCoreBrowserDomDriverV1,
        DriverError: BrowserDomDriverErrorV1
    });
})(globalThis);
