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

        openRecommendedActions(sourceElement) {
            const table = sourceElement.closest("table");
            if (!table) return;
            const requiresOperator = (row) => Array.from(row.cells)
                .some((cell) => cell.textContent.trim() === "Требуется решение оператора");
            if (!requiresOperator(sourceElement)) return;
            const rows = Array.from(table.querySelectorAll('tbody tr[data-mc-action-id]:not([disabled])'))
                .filter(requiresOperator)
                .sort((left, right) => Number(left.cells[0]?.textContent || 999) - Number(right.cells[0]?.textContent || 999));
            if (!rows.length) return;

            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "recommended");
            const title = this.documentObject.createElement("h2");
            title.textContent = "Рекомендуемые действия";
            const hint = this.documentObject.createElement("p");
            hint.textContent = "Выберите действие. Выполнение начнётся только после подтверждения.";
            const list = this.documentObject.createElement("div");
            list.className = "mc-action-dialog-list";
            rows.forEach((row) => {
                const item = this.documentObject.createElement("button");
                item.type = "button";
                item.className = "mc-action-dialog-item";
                const priority = row.cells[0]?.textContent?.trim() || "—";
                const action = row.cells[1]?.textContent?.trim() || "Действие";
                const reason = row.cells[2]?.textContent?.trim() || "";
                const itemTitle = this.documentObject.createElement("strong");
                itemTitle.textContent = `${priority}. ${action}`;
                const itemReason = this.documentObject.createElement("span");
                itemReason.textContent = reason;
                item.append(itemTitle, itemReason);
                item.addEventListener("click", async () => {
                    if (!globalObject.confirm(`Выполнить действие «${action}»?`)) return;
                    item.disabled = true;
                    try {
                        await this.actionSink({
                            actionId: row.dataset.mcActionId,
                            actionKind: row.dataset.mcActionKind,
                            interactionKind: "DOUBLE_CLICK",
                            targetId: row.dataset.mcTargetId || null,
                            commandCode: row.dataset.mcCommandCode || null,
                            policyClass: row.dataset.mcPolicyClass || null,
                            requiresApproval: row.dataset.mcRequiresApproval === "true",
                            reversible: row.dataset.mcReversible === "true",
                            rollbackCode: row.dataset.mcRollbackCode || null,
                            idempotencyKey: row.dataset.mcIdempotencyKey || null
                        });
                        dialog.close();
                    } finally {
                        item.disabled = false;
                    }
                });
                list.appendChild(item);
            });
            const close = this.documentObject.createElement("button");
            close.type = "button";
            close.className = "mc-action-dialog-close";
            close.textContent = "Отмена";
            close.addEventListener("click", () => dialog.close());
            dialog.addEventListener("close", () => dialog.remove());
            dialog.append(title, hint, list, close);
            this.documentObject.body.appendChild(dialog);
            dialog.showModal();
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
                element.setAttribute("data-mc-target-id", node.action.target_id || "");
                element.setAttribute("data-mc-command-code", node.action.command_code || "");
                element.setAttribute("data-mc-policy-class", node.action.policy_class || "");
                element.setAttribute("data-mc-requires-approval", String(Boolean(node.action.requires_approval)));
                element.setAttribute("data-mc-reversible", String(Boolean(node.action.reversible)));
                element.setAttribute("data-mc-rollback-code", node.action.rollback_code || "");
                element.setAttribute("data-mc-idempotency-key", node.action.idempotency_key || "");
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
                    const requiresDoubleClick = node.type === "table_row" || node.type === "card";
                    if (requiresDoubleClick) {
                        element.addEventListener("dblclick", () => this.openRecommendedActions(element));
                    } else {
                        element.addEventListener("click", () => emit("CLICK"));
                    }
                    element.addEventListener("keydown", (event) => {
                        if (event.key === "Enter" || (!requiresDoubleClick && event.key === " ")) {
                            event.preventDefault();
                            if (requiresDoubleClick) this.openRecommendedActions(element);
                            else emit("CLICK");
                        }
                    });
                }
            }
            if (context.displayValue !== null && context.displayValue !== undefined) {
                element.textContent = String(context.displayValue);
            }
            if (node.type === "table_cell" && node.node_id.endsWith(".confidence")) {
                const ratio = Math.max(0, Math.min(1, Number(context.displayValue) || 0));
                element.textContent = "";
                const progress = this.documentObject.createElement("progress");
                progress.max = 100;
                progress.value = Math.round(ratio * 100);
                progress.setAttribute("aria-label", `Уверенность ${progress.value} %`);
                const value = this.documentObject.createElement("span");
                value.textContent = `${progress.value} %`;
                element.append(progress, value);
            }
            while (this.stack.length > context.depth) this.stack.pop();
            const parent = this.stack.length === 0 ? this.mountElement : this.stack[this.stack.length - 1];
            parent.appendChild(element);
            this.stack.push(element);
            this.nodesRendered += 1;
        }

        endDocument() {
            this.mountElement.querySelectorAll('tbody tr[data-mc-action-id]').forEach((row) => {
                const requiresOperator = Array.from(row.cells)
                    .some((cell) => cell.textContent.trim() === "Требуется решение оператора");
                if (requiresOperator) {
                    row.setAttribute("data-mc-operator-required", "true");
                    return;
                }
                const confidence = row.querySelector('td[data-mc-node-id$=".confidence"]');
                const label = confidence?.querySelector("progress + span")?.textContent;
                if (confidence && label) confidence.textContent = label;
            });
            return Object.freeze({driverVersion: DRIVER_VERSION, nodesRendered: this.nodesRendered});
        }
    }

    globalObject.MarketCoreBrowserPlatformDriverV2 = Object.freeze({
        driverVersion: DRIVER_VERSION,
        Driver: BrowserPlatformDriverV2
    });
})(globalThis);
