"use strict";

(function installMarketCoreBrowserPlatformDriverV2(globalObject) {
    const DRIVER_VERSION = "marketcore.browser_platform_driver.v2";
    const ELEMENT_BY_NODE_TYPE = Object.freeze({
        workspace: "main", page: "section", header: "header", section: "section",
        grid: "div", card: "article", table: "table", table_head: "thead",
        table_body: "tbody", table_row: "tr", table_header_cell: "th",
        table_cell: "td", title: "h2", subtitle: "p", text: "span",
        metric_list: "dl", metric_row: "div", metric_label: "dt",
        metric_value: "dd", action: "button", badge: "span"
    });

    class BrowserPlatformDriverV2 {
        constructor(options) {
            if (!options || !options.documentObject || !options.mountElement) {
                throw new Error("BROWSER_PLATFORM_DRIVER_V2_OPTIONS_REQUIRED");
            }
            this.documentObject = options.documentObject;
            this.mountElement = options.mountElement;
            this.stack = [];
            this.nodesRendered = 0;
            this.actionSink = typeof options.actionSink === "function" ? options.actionSink : null;
        }

        beginDocument() {
            this.mountElement.replaceChildren();
            this.stack = [];
            this.nodesRendered = 0;
        }

        renderNode(node, context) {
            let tagName = ELEMENT_BY_NODE_TYPE[node.type];
            if (node.type === "title" && node.content && node.content.level_code === "PAGE") tagName = "h1";
            const element = this.documentObject.createElement(tagName);
            element.setAttribute("data-mc-node", node.type);
            element.setAttribute("data-mc-node-id", node.node_id);
            if (node.state && node.state.status_code) element.setAttribute("data-mc-status", node.state.status_code);
            if (node.action) {
                element.setAttribute("data-mc-action-id", node.action.action_id);
                element.setAttribute("data-mc-action-kind", node.action.action_kind);
                if (!node.action.enabled) element.setAttribute("disabled", "disabled");
                if (node.action.enabled) {
                    const emit = (interactionKind) => {
                        const intent = Object.freeze({
                            actionId: node.action.action_id,
                            actionKind: node.action.action_kind,
                            interactionKind,
                            targetId: node.action.target_id || null,
                            commandCode: node.action.command_code || null,
                            policyClass: node.action.policy_class || null,
                            requiresApproval: Boolean(node.action.requires_approval),
                            reversible: Boolean(node.action.reversible),
                            rollbackCode: node.action.rollback_code || null,
                            idempotencyKey: node.action.idempotency_key || null
                        });
                        if (this.actionSink) this.actionSink(intent);
                    };
                    element.setAttribute("role", node.action.action_kind === "NAVIGATE" ? "link" : "button");
                    element.setAttribute("tabindex", "0");
                    element.addEventListener("click", () => emit("CLICK"));
                    element.addEventListener("dblclick", () => emit("DOUBLE_CLICK"));
                    element.addEventListener("keydown", (event) => {
                        if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            emit("CLICK");
                        }
                    });
                }
            }
            if (context.displayValue !== null && context.displayValue !== undefined) {
                element.textContent = String(context.displayValue);
            }
            while (this.stack.length > context.depth) this.stack.pop();
            const parent = this.stack.length === 0 ? this.mountElement : this.stack[this.stack.length - 1];
            parent.appendChild(element);
            this.stack.push(element);
            this.nodesRendered += 1;
        }

        endDocument() {
            return Object.freeze({driverVersion: DRIVER_VERSION, nodesRendered: this.nodesRendered});
        }
    }

    globalObject.MarketCoreBrowserPlatformDriverV2 = Object.freeze({
        driverVersion: DRIVER_VERSION,
        Driver: BrowserPlatformDriverV2
    });
})(globalThis);
