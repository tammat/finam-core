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

        announce(message, state = "INFO") {
            let toast = this.documentObject.querySelector("[data-mc-ux-toast]");
            if (!toast) {
                toast = this.documentObject.createElement("div");
                toast.setAttribute("data-mc-ux-toast", "true");
                toast.setAttribute("role", "status");
                toast.setAttribute("aria-live", "polite");
                this.documentObject.body.appendChild(toast);
            }
            toast.dataset.state = state;
            toast.textContent = message;
            globalObject.clearTimeout(this.toastTimer);
            this.toastTimer = globalObject.setTimeout(() => toast.remove(), 2600);
        }

        selectInteractive(element, hint) {
            this.documentObject.querySelectorAll('[data-mc-selected="true"]')
                .forEach((selected) => selected.removeAttribute("data-mc-selected"));
            element.setAttribute("data-mc-selected", "true");
            this.announce(hint);
        }

        openResearchActions(row) {
            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "research");
            const title = this.documentObject.createElement("h2");
            title.textContent = "Рекомендуемые действия";
            const hint = this.documentObject.createElement("p");
            hint.textContent = "Выберите процесс. Заявку выполнит системный планировщик.";
            const list = this.documentObject.createElement("div");
            list.className = "mc-action-dialog-list";
            const recommendationCell = row.querySelector('[data-mc-node-id$=".recommendation"]');
            let options = [];
            try { options = JSON.parse(recommendationCell?.dataset.mcActions || "[]"); }
            catch (error) { options = []; }
            const processId = recommendationCell?.dataset.mcProcessId || null;
            if (!options.length) {
                hint.textContent = "Для текущего состояния действия не требуются.";
            }
            options.forEach((option) => {
                const button = this.documentObject.createElement("button");
                button.type = "button";
                button.className = "mc-action-dialog-item";
                const label = this.documentObject.createElement("strong");
                label.textContent = option.label;
                const detail = this.documentObject.createElement("span");
                detail.textContent = option.detail;
                button.append(label, detail);
                button.addEventListener("click", async () => {
                    if (!globalObject.confirm(`Подтвердить: ${option.label}?`)) return;
                    button.disabled = true;
                    this.announce("Заявка ставится в очередь…", "RUNNING");
                    try {
                        await this.actionSink({
                            actionId: option.action_id, actionKind: "COMMAND", interactionKind: "DOUBLE_CLICK",
                            targetId: processId, commandCode: option.command_code,
                            policyClass: option.policy_class, requiresApproval: false, reversible: true,
                            rollbackCode: option.rollback_code, idempotencyKey: "client.request"
                        });
                        dialog.close(); dialog.remove();
                        this.announce("Заявка принята системой", "SUCCESS");
                    } catch (error) {
                        button.disabled = false;
                        this.announce("Не удалось поставить заявку в очередь", "ERROR");
                    }
                });
                list.appendChild(button);
            });
            const close = this.documentObject.createElement("button");
            close.type = "button"; close.className = "mc-action-dialog-close"; close.textContent = "Закрыть";
            close.addEventListener("click", () => { dialog.close(); dialog.remove(); });
            dialog.append(title, hint, list, close);
            this.documentObject.body.appendChild(dialog);
            dialog.showModal();
        }

        async activateInteractive(element, emit, interactionKind, pendingLabel) {
            if (element.getAttribute("aria-busy") === "true") return;
            element.setAttribute("aria-busy", "true");
            this.announce(pendingLabel, "RUNNING");
            try {
                await emit(interactionKind);
                this.announce("Открыто", "SUCCESS");
            } catch (error) {
                globalObject.console.error("MARKETCORE_INTERACTION_FAILED", error);
                this.announce("Не удалось выполнить действие. Обновите страницу.", "ERROR");
            } finally {
                element.removeAttribute("aria-busy");
            }
        }

        openRecommendedActions(sourceElement) {
            const table = sourceElement.closest("table");
            if (!table) return;
            if (sourceElement.dataset.mcActionKind === "NAVIGATE") {
                this.openFunnelActions(sourceElement);
                return;
            }
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
                const commandLabel = row.dataset.mcActionId === "operator.decision.measure"
                    ? "Проверить результат"
                    : "Принять рекомендацию";
                const itemTitle = this.documentObject.createElement("strong");
                itemTitle.textContent = `${priority}. ${commandLabel}`;
                const itemReason = this.documentObject.createElement("span");
                itemReason.textContent = `${action}: ${reason}`;
                item.append(itemTitle, itemReason);
                item.addEventListener("click", async () => {
                    if (!globalObject.confirm(`${commandLabel}: «${action}»?`)) return;
                    item.disabled = true;
                    dialog.close();
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

        openFunnelActions(row) {
            const stage = row.cells[0]?.textContent?.trim() || "этап";
            const status = row.cells[3]?.textContent?.trim() || "Статус не определён";
            const recommendations = {
                "Исследования": "Проверить свежесть данных и запустить следующий исследовательский цикл",
                "Кандидаты": "Проверить параметры и воспроизводимость кандидатов",
                "Подтверждённое преимущество": "Проверить критерии подтверждения преимущества",
                "Вневыборочная проверка": "Провести cost-adjusted OOS и проверить фолды",
                "Форвардное наблюдение": "Проверить чистую Forward-когорту и накопление наблюдений",
                "Теневое наблюдение": "Проверить сделки, издержки и достаточность Shadow-выборки",
                "Paper": "Проверить готовность к Paper без реальных заявок",
                "Runtime": "Проверить свежесть Runtime и критерии допуска",
                "Live": "Проверить риск-разрешение; торговлю не включать без PASS",
                "Profit": "Проверить чистый PnL после всех издержек"
            };
            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "funnel");
            const title = this.documentObject.createElement("h2");
            title.textContent = "Рекомендуемые действия";
            const hint = this.documentObject.createElement("p");
            hint.textContent = `${stage} · ${status}`;
            const list = this.documentObject.createElement("div");
            list.className = "mc-action-dialog-list";
            const open = this.documentObject.createElement("button");
            open.type = "button";
            open.className = "mc-action-dialog-item";
            const openTitle = this.documentObject.createElement("strong");
            openTitle.textContent = `Открыть этап «${stage}»`;
            const detail = this.documentObject.createElement("span");
            detail.textContent = recommendations[stage] || "Открыть ответственный режим и проверить причину статуса";
            open.append(openTitle, detail);
            open.addEventListener("click", async () => {
                open.disabled = true;
                dialog.close();
                try {
                    await this.actionSink({
                        actionId: row.dataset.mcActionId,
                        actionKind: row.dataset.mcActionKind,
                        interactionKind: "DOUBLE_CLICK",
                        targetId: row.dataset.mcTargetId || null
                    });
                } finally {
                    open.disabled = false;
                }
            });
            list.appendChild(open);
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
                        return this.actionSink ? this.actionSink(intent) : Promise.resolve(null);
                    };
                    element.setAttribute("role", node.action.action_kind === "NAVIGATE" ? "link" : "button");
                    element.setAttribute("tabindex", "0");
                    const isTableRow = node.type === "table_row";
                    const isContainer = node.type === "card";
                    const isCommandButton = node.type === "action" && node.action.action_kind === "COMMAND";
                    const requiresDoubleClick = isTableRow || isContainer || isCommandButton;
                    if (requiresDoubleClick) {
                        element.setAttribute("data-mc-interaction", "double-click");
                        element.setAttribute("title", isTableRow
                            ? "Двойной клик — открыть рекомендуемые действия"
                            : isCommandButton
                                ? "Двойной клик — выполнить после подтверждения"
                                : "Двойной клик — открыть раздел");
                    }
                    if (isTableRow) {
                        element.addEventListener("click", () => this.selectInteractive(element,"Двойной клик — открыть рекомендуемые действия"));
                        element.addEventListener("dblclick", (event) => {
                            const cell = event.target.closest && event.target.closest('[data-mc-node="table_cell"]');
                            const isResearchRow = element.getAttribute("data-mc-node-id")?.startsWith("research.audit.");
                            const isRecommendation = cell?.getAttribute("data-mc-node-id")?.endsWith(".recommendation");
                            if (isResearchRow && isRecommendation) this.openResearchActions(element);
                            else if (isResearchRow) this.announce("Запуск доступен двойным кликом в колонке «Далее»");
                            else this.openRecommendedActions(element);
                        });
                    } else if (isContainer) {
                        element.addEventListener("click", () => this.selectInteractive(element,"Двойной клик — открыть раздел"));
                        element.addEventListener("dblclick", () => this.activateInteractive(element,emit,"DOUBLE_CLICK","Открываю раздел…"));
                    } else if (isCommandButton) {
                        element.addEventListener("click", () => this.selectInteractive(element,"Двойной клик — выполнить действие"));
                        element.addEventListener("dblclick", async () => {
                            if (globalObject.confirm("Подтвердить выполнение действия?")) {
                                await this.activateInteractive(element,emit,"DOUBLE_CLICK","Выполняю действие…");
                            }
                        });
                    } else {
                        element.addEventListener("click", () => emit("CLICK"));
                    }
                    element.addEventListener("keydown", (event) => {
                        if (event.key === "Enter" || (!requiresDoubleClick && event.key === " ")) {
                            event.preventDefault();
                            if (isTableRow) this.openRecommendedActions(element);
                            else if (isContainer) this.activateInteractive(element,emit,"DOUBLE_CLICK","Открываю раздел…");
                            else if (isCommandButton && globalObject.confirm("Подтвердить выполнение действия?")) this.activateInteractive(element,emit,"DOUBLE_CLICK","Выполняю действие…");
                            else emit("CLICK");
                        }
                    });
                }
            }
            if (context.displayValue !== null && context.displayValue !== undefined) {
                element.textContent = String(context.displayValue);
            }
            if (context.tooltipValue) {
                element.setAttribute("title", String(context.tooltipValue));
                element.setAttribute("aria-label", `${String(context.displayValue || "")}. ${String(context.tooltipValue)}`);
            }
            if (node.type === "table_cell" && node.node_id.endsWith(".recommendation") && node.content?.message_args) {
                element.dataset.mcProcessId = String(node.content.message_args.process_id || "");
                element.dataset.mcActions = JSON.stringify(node.content.message_args.actions || []);
            }
            if (node.type === "table_cell" && node.node_id.endsWith(".status")) {
                const label = String(context.displayValue || "");
                const progressByLabel = {
                    "Требуется решение оператора": 10,
                    "Принято к рассмотрению": 50,
                    "Результат измерен": 100,
                    "Заблокировано": 0,
                    "Просрочено": 0,
                    "Выполнено": 100,
                    "Ошибка": 0,
                    "Выполняется": 50,
                    "Ожидает": 10
                };
                element.textContent = "";
                const progress = this.documentObject.createElement("progress");
                progress.max = 100;
                const processProgress = Number(node.content?.message_args?.progress_pct);
                progress.value = Number.isFinite(processProgress) ? Math.max(0, Math.min(100, processProgress)) : (progressByLabel[label] ?? 0);
                progress.setAttribute("aria-label", `${label}: ${progress.value} %`);
                const value = this.documentObject.createElement("span");
                value.textContent = label;
                element.append(progress, value);
            }
            if (node.type === "table_cell" && node.content && node.content.column_code === "progress_pct") {
                const numeric = Math.max(0, Math.min(100, Number(node.content.value || 0)));
                element.textContent = "";
                element.classList.add("mc-progress-cell");
                const progress = this.documentObject.createElement("progress");
                progress.max = 100;
                progress.value = numeric;
                progress.setAttribute("aria-label", `${numeric} %`);
                const value = this.documentObject.createElement("span");
                value.textContent = `${numeric.toLocaleString(undefined, {maximumFractionDigits: 1})} %`;
                element.append(progress, value);
            }
            while (this.stack.length > context.depth) this.stack.pop();
            const parent = this.stack.length === 0 ? this.mountElement : this.stack[this.stack.length - 1];
            parent.appendChild(element);
            this.stack.push(element);
            this.nodesRendered += 1;
        }

        endDocument() {
            this.mountElement.querySelectorAll('[data-mc-node="table"]').forEach((table) => {
                if (!table.querySelector('tbody [data-mc-node="table_row"]')) table.remove();
            });
            this.mountElement.querySelectorAll('[data-mc-node="grid"]').forEach((grid) => {
                if (!grid.querySelector('[data-mc-node="card"]')) grid.remove();
            });
            Array.from(this.mountElement.querySelectorAll('[data-mc-node="section"]')).reverse().forEach((section) => {
                const hasContent = section.querySelector([
                    '[data-mc-node="table"]', '[data-mc-node="grid"]', '[data-mc-node="card"]',
                    '[data-mc-node="metric_list"]', '[data-mc-node="action"]', '[data-mc-node="text"]',
                    '[data-mc-node="badge"]'
                ].join(','));
                if (!hasContent) section.remove();
            });
            this.mountElement.querySelectorAll('tbody tr[data-mc-action-id]').forEach((row) => {
                const requiresOperator = Array.from(row.cells)
                    .some((cell) => cell.textContent.trim() === "Требуется решение оператора");
                if (requiresOperator) {
                    row.setAttribute("data-mc-operator-required", "true");
                    return;
                }
            });
            return Object.freeze({driverVersion: DRIVER_VERSION, nodesRendered: this.nodesRendered});
        }
    }

    globalObject.MarketCoreBrowserPlatformDriverV2 = Object.freeze({
        driverVersion: DRIVER_VERSION,
        Driver: BrowserPlatformDriverV2
    });
})(globalThis);
