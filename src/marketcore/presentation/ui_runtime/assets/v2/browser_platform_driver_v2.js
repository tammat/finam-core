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
            this.translate = typeof options.translate === "function" ? options.translate : null;
            this.localeCode = options.localeCode || "ru-RU";
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
            toast.replaceChildren();
            if (state === "RUNNING") {
                const logo = this.documentObject.createElement("img");
                logo.className = "mc-loading-logo";
                logo.src = "/assets/marketcore/ui-runtime/v2/marketcore-logo-v2.png";
                logo.alt = "";
                logo.setAttribute("aria-hidden", "true");
                toast.appendChild(logo);
            }
            const label = this.documentObject.createElement("span");
            label.textContent = state === "RUNNING" ? "Загрузка" : message;
            toast.appendChild(label);
            toast.setAttribute("aria-label", message);
            globalObject.clearTimeout(this.toastTimer);
            this.toastTimer = globalObject.setTimeout(() => toast.remove(), 2600);
        }

        selectInteractive(element, hint) {
            this.documentObject.querySelectorAll('[data-mc-selected="true"]')
                .forEach((selected) => selected.removeAttribute("data-mc-selected"));
            element.setAttribute("data-mc-selected", "true");
            this.announce(hint);
        }

        localized(key, fallback) {
            if (!this.translate) return fallback;
            try {
                const value = this.translate(key, {}, this.localeCode);
                return value && value !== key ? String(value) : fallback;
            } catch (_error) {
                return fallback;
            }
        }

        showActionDialog(dialog) {
            dialog.querySelectorAll(".mc-action-dialog-close").forEach((button) => button.remove());
            dialog.addEventListener("click", (event) => {
                if (event.target === dialog) {
                    dialog.close();
                    return;
                }
                const action = event.target.closest?.(".mc-action-dialog-item");
                if (!action || action.dataset.mcDoubleClickActivation === "true") return;
                event.preventDefault();
                event.stopImmediatePropagation();
            }, true);
            dialog.addEventListener("dblclick", (event) => {
                const action = event.target.closest?.(".mc-action-dialog-item");
                if (!action || action.disabled) return;
                event.preventDefault();
                event.stopImmediatePropagation();
                action.dataset.mcDoubleClickActivation = "true";
                action.click();
                delete action.dataset.mcDoubleClickActivation;
            }, true);
            dialog.addEventListener("close", () => dialog.remove(), {once: true});
            dialog.showModal();
        }

        tableSortKey(table) {
            const tableId = table?.getAttribute("data-mc-node-id") || "table";
            return `marketcore.workspace-v2.sort:${tableId}`;
        }

        sortableValue(cell) {
            const text = String(cell?.textContent || "").replace(/\u00a0/g, " ").trim();
            const date = text.match(/^(\d{2})\.(\d{2})\.(\d{4})(?:,?\s+(\d{2}):(\d{2})(?::(\d{2}))?)?$/);
            if (date) {
                return {kind: "number", value: Date.UTC(
                    Number(date[3]), Number(date[2]) - 1, Number(date[1]),
                    Number(date[4] || 0), Number(date[5] || 0), Number(date[6] || 0)
                )};
            }
            const ratio = text.match(/^([+-]?[\d\s]+(?:[.,]\d+)?)\s*\/\s*([\d\s]+(?:[.,]\d+)?)$/);
            if (ratio) {
                const numerator = Number(ratio[1].replace(/\s/g, "").replace(",", "."));
                const denominator = Number(ratio[2].replace(/\s/g, "").replace(",", "."));
                return {kind: "number", value: denominator ? numerator / denominator : numerator};
            }
            const numeric = text.match(/^([+-]?[\d\s]+(?:[.,]\d+)?)\s*(?:%|₽|р\.?|сек\.?|мс)?$/i);
            if (numeric) {
                return {kind: "number", value: Number(numeric[1].replace(/\s/g, "").replace(",", "."))};
            }
            return {kind: "text", value: text.toLocaleLowerCase(this.localeCode)};
        }

        sortTable(header, requestedDirection = null, persist = true) {
            const table = header?.closest("table");
            const headerRow = header?.parentElement;
            if (!table || !headerRow) return;
            const columnIndex = Array.from(headerRow.children).indexOf(header);
            if (columnIndex < 0) return;
            const current = header.getAttribute("data-mc-sort-direction");
            const direction = requestedDirection || (current === "ascending" ? "descending" : "ascending");
            table.querySelectorAll('[data-mc-node="table_header_cell"]').forEach((item) => {
                item.removeAttribute("data-mc-sort-direction");
                item.setAttribute("aria-sort", "none");
            });
            header.setAttribute("data-mc-sort-direction", direction);
            header.setAttribute("aria-sort", direction);
            const rows = Array.from(table.querySelectorAll('tr[data-mc-node="table_row"]'))
                .filter((row) => row.querySelector('[data-mc-node="table_cell"]'));
            const parents = new Set(rows.map((row) => row.parentElement));
            parents.forEach((parent) => {
                const sortableRows = rows.filter((row) => row.parentElement === parent && row.children[columnIndex]);
                sortableRows.map((row, index) => ({row, index, key:this.sortableValue(row.children[columnIndex])}))
                    .sort((left, right) => {
                        let result;
                        if (left.key.kind === "number" && right.key.kind === "number") {
                            result = left.key.value - right.key.value;
                        } else {
                            result = String(left.key.value).localeCompare(String(right.key.value), this.localeCode, {numeric:true});
                        }
                        if (result === 0) result = left.index - right.index;
                        return direction === "ascending" ? result : -result;
                    })
                    .forEach(({row}) => parent.appendChild(row));
            });
            if (persist) {
                try {
                    globalObject.sessionStorage.setItem(this.tableSortKey(table), JSON.stringify({columnIndex, direction}));
                } catch (_error) { /* storage may be unavailable in embedded views */ }
            }
            const messageKey = direction === "ascending" ? "table.sort.ascending" : "table.sort.descending";
            const fallback = direction === "ascending" ? "По возрастанию" : "По убыванию";
            if (persist) this.announce(this.localized(messageKey, fallback));
        }

        restoreTableSorts() {
            this.mountElement.querySelectorAll('[data-mc-node="table"]').forEach((table) => {
                try {
                    const state = JSON.parse(globalObject.sessionStorage.getItem(this.tableSortKey(table)) || "null");
                    if (!state || !Number.isInteger(state.columnIndex)) return;
                    const header = table.querySelectorAll('[data-mc-node="table_header_cell"]')[state.columnIndex];
                    if (header) this.sortTable(header, state.direction, false);
                } catch (_error) { /* ignore stale or unavailable storage */ }
            });
        }

        applyScoutFilter(table, filter) {
            const rows = table.querySelectorAll('tbody tr[data-mc-node-id^="research.scout."]');
            rows.forEach((row) => {
                const nodeId = row.getAttribute("data-mc-node-id") || "";
                const decision = (nodeId.match(/^research\.scout\.([a-z_]+)\.\d+$/) || [])[1] || "";
                row.hidden = !(filter === "all" || filter === decision ||
                    (filter === "active" && (decision === "selected" || decision === "reserve")));
            });
            table.dataset.mcScoutFilter = filter;
            const toolbar = table.previousElementSibling;
            toolbar?.querySelectorAll("button").forEach((button) =>
                button.setAttribute("aria-pressed", String(button.dataset.filter === filter)));
        }

        ensureScoutFilters(row) {
            const table = row.closest("table");
            if (!table || table.dataset.mcScoutFiltersReady === "true") return;
            table.dataset.mcScoutFiltersReady = "true";
            const toolbar = this.documentObject.createElement("div");
            toolbar.className = "mc-scout-filters";
            toolbar.setAttribute("role", "toolbar");
            toolbar.setAttribute("aria-label", "Фильтр разведки инструментов");
            [["active","Активные"],["selected","Выбраны"],["reserve","Резерв"],
             ["backfill","Сбор данных"],["excluded","Исключены"],["all","Все"]].forEach(([code,label]) => {
                const button=this.documentObject.createElement("button");
                button.type="button"; button.dataset.filter=code; button.textContent=label;
                button.addEventListener("click",()=>this.applyScoutFilter(table,code));
                toolbar.appendChild(button);
            });
            table.parentNode.insertBefore(toolbar,table);
            globalObject.setTimeout(()=>this.applyScoutFilter(table,"active"),0);
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
            let submitting = false;
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
                    button.disabled = true;
                    dialog.close();
                    dialog.remove();
                    this.announce("Заявка ставится в очередь…", "RUNNING");
                    try {
                        await this.actionSink({
                            actionId: option.action_id, actionKind: "COMMAND", interactionKind: "DOUBLE_CLICK",
                            targetId: processId, commandCode: option.command_code,
                            policyClass: option.policy_class, requiresApproval: false, reversible: true,
                            rollbackCode: option.rollback_code, idempotencyKey: "client.request"
                        });
                        this.announce("Заявка принята системой", "SUCCESS");
                    } catch (error) {
                        button.disabled = false;
                        this.announce("Не удалось поставить заявку в очередь", "ERROR");
                    }
                });
                list.appendChild(button);
            });
            const rowState = row.querySelector('[data-mc-node-id$=".status"]')?.textContent?.trim() || "";
            if (rowState === "Ошибка" || rowState === "Пропущено") {
                const priorityButton = this.documentObject.createElement("button");
                priorityButton.type = "button";
                priorityButton.className = "mc-action-dialog-item";
                const priorityLabel = this.documentObject.createElement("strong");
                priorityLabel.textContent = "Повторить срочно";
                const priorityDetail = this.documentObject.createElement("span");
                priorityDetail.textContent = "Поставить новый системный цикл первым в исследовательской очереди";
                priorityButton.append(priorityLabel, priorityDetail);
                priorityButton.addEventListener("click", async () => {
                    priorityButton.disabled = true;
                    dialog.close();
                    dialog.remove();
                    this.setRowStatus(row, "Выполняется", 50, "RUNNING");
                    try {
                        await this.actionSink({
                            actionId: "research.edge_search.run", actionKind: "COMMAND",
                            interactionKind: "DOUBLE_CLICK", targetId: "MAX_PRIORITY",
                            commandCode: "RESEARCH.RUN_EDGE_SEARCH", policyClass: "RESEARCH_MAINTENANCE",
                            requiresApproval: false, reversible: true,
                            rollbackCode: "RESEARCH.CANCEL_PENDING_REQUEST", idempotencyKey: "client.request"
                        });
                        this.setRowStatus(row, "Ожидает", 10, "WARNING");
                        this.announce("Приоритетный перезапуск поставлен в очередь", "SUCCESS");
                    } catch (error) {
                        this.setRowStatus(row, "Ошибка", 0, "FAIL");
                        this.announce("Не удалось поставить приоритетный перезапуск", "ERROR");
                    }
                });
                list.appendChild(priorityButton);
            }
            const close = this.documentObject.createElement("button");
            close.type = "button"; close.className = "mc-action-dialog-close"; close.textContent = "Закрыть";
            close.addEventListener("click", () => { dialog.close(); dialog.remove(); });
            dialog.append(title, hint, list, close);
            this.documentObject.body.appendChild(dialog);
            this.showActionDialog(dialog);
        }

        openMethodologyActions(row) {
            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const cells = row.cells;
            const gate = cells[0]?.textContent?.trim() || "Методологическая проверка";
            const failed = cells[1]?.textContent?.trim() || "0";
            const passed = cells[2]?.textContent?.trim() || "0";
            const skipped = cells[3]?.textContent?.trim() || "0";
            const failPct = cells[4]?.textContent?.trim() || "0";
            const reason = cells[5]?.textContent?.trim() || "Нет пояснения";
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "methodology");
            const title = this.documentObject.createElement("h2");
            title.textContent = gate;
            const hint = this.documentObject.createElement("p");
            hint.textContent = `Провалено: ${failed}; пройдено: ${passed}; не проверялось: ${skipped}; отказов среди проверенных: ${failPct}%. ${reason}`;
            const list = this.documentObject.createElement("div");
            list.className = "mc-action-dialog-list";
            const add = (label, detail, handler) => {
                const button = this.documentObject.createElement("button");
                button.type = "button"; button.className = "mc-action-dialog-item";
                const strong = this.documentObject.createElement("strong"); strong.textContent = label;
                const span = this.documentObject.createElement("span"); span.textContent = detail;
                button.append(strong, span); button.addEventListener("click", handler); list.appendChild(button);
            };
            add("Показать доказательства", "Открыть подробную методологическую раскладку", () => {
                hint.textContent = `${gate}. ${hint.textContent} Последующие ворота учитываются только после прохождения предыдущих.`;
            });
            add("Повторить адресно", "Система создаст новый сценарий по первой реальной причине отказа", async () => {
                dialog.close(); dialog.remove();
                try {
                    await this.actionSink({
                        actionId:"research.methodology.recheck", actionKind:"COMMAND", interactionKind:"DOUBLE_CLICK",
                        targetId:row.dataset.mcTargetId || gate, commandCode:"RESEARCH.RUN_EDGE_SEARCH",
                        policyClass:"RESEARCH_MAINTENANCE", requiresApproval:false, reversible:true,
                        rollbackCode:"RESEARCH.CANCEL_PENDING_REQUEST", idempotencyKey:"client.request"
                    });
                    this.announce("Адресная проверка поставлена в системную очередь", "SUCCESS");
                } catch (error) { this.announce("Не удалось поставить проверку в очередь", "ERROR"); }
            });
            add("Оставить блокировку", "Критерии PASS не изменяются", () => { dialog.close(); dialog.remove(); });
            const close = this.documentObject.createElement("button");
            close.type="button"; close.className="mc-action-dialog-close"; close.textContent="Закрыть";
            close.addEventListener("click",()=>{dialog.close();dialog.remove();});
            dialog.append(title,hint,list,close); this.documentObject.body.appendChild(dialog); this.showActionDialog(dialog);
        }

        openGovernanceActions(card) {
            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const nodeId = card.getAttribute("data-mc-node-id") || "";
            const code = nodeId.replace("research.tile.", "");
            const titleText = card.querySelector('[data-mc-node="title"]')?.textContent?.trim() || "Контроль метода";
            const value = card.querySelector('[data-mc-node="metric_value"]')?.textContent?.trim() || "0";
            const definitions = {
                global_trials: ["Проверенные варианты", "Сколько вариантов прошло методологические проверки."],
                global_pass: ["Значимые PASS", "Сколько вариантов подтвердили статистическую значимость."],
                holdout: ["Чистый holdout", "Сколько проверок выполнено на независимых данных без пересечения фолдов."],
                pnl_units: ["P&L готово", "Сколько результатов прибыли и убытка пригодно для методологической оценки."],
                pnl_blocks: ["Ошибки P&L", "Сколько результатов заблокировано из-за неполного или неподтверждённого P&L."],
                equities: ["PASS по акциям", "Сколько акционных связок прошло строгие критерии PASS."],
                futures: ["PASS по фьючерсам", "Сколько фьючерсных связок прошло строгие критерии PASS."],
                portfolio: ["В портфель", "Сколько подтверждённых связок прошло портфельный отбор."]
            };
            const [label, explanation] = definitions[code] || [titleText, "Текущий показатель методологического контроля."];
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "governance");
            const title = this.documentObject.createElement("h2");
            title.textContent = label;
            const hint = this.documentObject.createElement("p");
            hint.textContent = `Текущее значение: ${value}. ${explanation}`;
            const list = this.documentObject.createElement("div");
            list.className = "mc-action-dialog-list";
            const add = (buttonLabel, detail, handler) => {
                const button = this.documentObject.createElement("button");
                button.type = "button"; button.className = "mc-action-dialog-item";
                const strong = this.documentObject.createElement("strong"); strong.textContent = buttonLabel;
                const span = this.documentObject.createElement("span"); span.textContent = detail;
                button.append(strong, span); button.addEventListener("click", handler); list.appendChild(button);
            };
            add("Показать пояснение", "Показать смысл показателя и допустимый следующий шаг", () => {
                hint.textContent = `Текущее значение: ${value}. ${explanation} Критерии PASS при выполнении команды не ослабляются.`;
            });
            const refreshOnly = new Set(["pnl_units", "pnl_blocks", "holdout", "portfolio"]);
            add(
                refreshOnly.has(code) ? "Обновить оценку" : "Продолжить строгий поиск",
                refreshOnly.has(code) ? "Пересчитать показатель по актуальным данным БД" : "Поставить следующий checkpointed-цикл в очередь",
                async () => {
                    dialog.close(); dialog.remove();
                    card.setAttribute("data-mc-status", "WARNING");
                    try {
                        await this.actionSink({
                            actionId: refreshOnly.has(code) ? "research.request.refresh" : "research.edge_search.run",
                            actionKind: "COMMAND", interactionKind: "DOUBLE_CLICK", targetId: nodeId,
                            commandCode: refreshOnly.has(code) ? "RESEARCH.REQUEST_REFRESH" : "RESEARCH.RUN_EDGE_SEARCH",
                            policyClass: "RESEARCH_MAINTENANCE", requiresApproval: false, reversible: true,
                            rollbackCode: refreshOnly.has(code) ? null : "RESEARCH.CANCEL_PENDING_REQUEST",
                            idempotencyKey: `governance.${code}`
                        });
                        this.announce("Ожидает выполнения системной очередью", "SUCCESS");
                    } catch (error) {
                        card.setAttribute("data-mc-status", "FAIL");
                        this.announce("Не удалось поставить действие в очередь", "ERROR");
                    }
                }
            );
            dialog.append(title, hint, list);
            this.documentObject.body.appendChild(dialog);
            this.showActionDialog(dialog);
        }

        openUniverseActions(row) {
            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const table = row.closest("table");
            const headers = Array.from(table?.querySelectorAll('[data-mc-node="table_header_cell"]') || [])
                .map((cell) => cell.textContent.trim().toLocaleLowerCase(this.localeCode));
            const columnIndex = (label) => headers.findIndex((header) => header.includes(label));
            const symbol = row.cells[1]?.textContent?.trim() || "";
            const reasonIndex = columnIndex("причин");
            const categoryIndex = columnIndex("категор");
            const scoreIndex = columnIndex("оцен");
            const decisionIndex = columnIndex("решен");
            const reason = row.cells[reasonIndex]?.textContent?.trim() || "Нет объяснения";
            const category = row.cells[categoryIndex]?.textContent?.trim() || "—";
            const score = row.cells[scoreIndex]?.textContent?.trim() || "—";
            const decision = row.cells[decisionIndex]?.textContent?.trim() || "—";
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "universe");
            const title = this.documentObject.createElement("h2");
            title.textContent = symbol;
            const hint = this.documentObject.createElement("p");
            hint.textContent = "Решение системы уже действует. Выбор оператора необязателен и применяется только к следующему циклу.";
            const list = this.documentObject.createElement("div");
            list.className = "mc-action-dialog-list";
            const addButton = (label, detail, handler) => {
                const button = this.documentObject.createElement("button");
                button.type = "button"; button.className = "mc-action-dialog-item";
                const strong = this.documentObject.createElement("strong"); strong.textContent = label;
                const span = this.documentObject.createElement("span"); span.textContent = detail;
                button.append(strong, span); button.addEventListener("click", handler); list.appendChild(button);
            };
            const submit = async (actionId, commandCode, targetId, label) => {
                if (submitting) return;
                submitting = true;
                dialog.close(); dialog.remove();
                try {
                    await this.actionSink({actionId,actionKind:"COMMAND",interactionKind:"DOUBLE_CLICK",targetId,
                        commandCode,policyClass:"RESEARCH_MAINTENANCE",requiresApproval:false,reversible:true,
                        rollbackCode:"RESEARCH.UNIVERSE_CLEAR_OVERRIDE",idempotencyKey:"client.request"});
                    this.announce("Заявка применена к следующему циклу", "SUCCESS");
                } catch (error) {
                    this.announce("Не удалось применить заявку", "ERROR");
                }
            };
            addButton("Почему выбрано", reason, () => {
                hint.textContent = `${symbol}: решение — ${decision}; категория — ${category}; оценка — ${score}; причина — ${reason}.`;
            });
            addButton("Закрепить в следующем цикле", "Обязательно включить инструмент независимо от нового рейтинга", () =>
                submit("research.universe.include_next","RESEARCH.UNIVERSE_INCLUDE_NEXT",symbol,"включить инструмент"));
            addButton("Исключить из следующего цикла", "Не затрагивать текущий цикл; убрать инструмент только из следующего", () =>
                submit("research.universe.exclude_next","RESEARCH.UNIVERSE_EXCLUDE_NEXT",symbol,"исключить инструмент"));
            addButton("Изменить приоритет", "1 — максимальный, 100 — минимальный", () => {
                const value = Number(globalObject.prompt("Приоритет от 1 до 100", "50"));
                if (!Number.isInteger(value) || value < 1 || value > 100) return this.announce("Введите целое число от 1 до 100", "ERROR");
                return submit("research.universe.priority","RESEARCH.UNIVERSE_SET_PRIORITY",`${symbol}|${value}`,`приоритет ${value}`);
            });
            const close = this.documentObject.createElement("button");
            close.type="button"; close.className="mc-action-dialog-close"; close.textContent="Закрыть";
            close.addEventListener("click",()=>{dialog.close();dialog.remove();});
            dialog.append(title,hint,list,close); this.documentObject.body.appendChild(dialog); this.showActionDialog(dialog);
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

        setRowStatus(row, label, progressValue, statusCode) {
            if (!row) return;
            const statusCell = row.querySelector(
                '[data-mc-column-code="status"], [data-mc-node-id$=".status"]'
            );
            if (!statusCell) return;
            const progress = this.documentObject.createElement("progress");
            progress.max = 100;
            progress.value = Math.max(0, Math.min(100, Number(progressValue) || 0));
            progress.setAttribute("aria-label", `${label}: ${progress.value} %`);
            const value = this.documentObject.createElement("span");
            value.textContent = label;
            statusCell.replaceChildren(progress, value);
            statusCell.setAttribute("data-mc-transient-status", statusCode);
            row.setAttribute("data-mc-status", statusCode);
        }

        openRowResolution(row) {
            const table = row.closest("table");
            if (!table) return;
            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const headers = Array.from(table.querySelectorAll('[data-mc-node="table_header_cell"]'));
            const values = Array.from(row.cells).map((cell) => cell.textContent.trim());
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "row-resolution");
            const title = this.documentObject.createElement("h2");
            title.textContent = `Решение: ${values[0] || "выбранная строка"}`;
            const hint = this.documentObject.createElement("p");
            hint.textContent = "Исполняемая команда будет записана в БД и выполнена системным планировщиком.";
            const facts = this.documentObject.createElement("dl");
            facts.className = "mc-v2-values";
            values.forEach((value, index) => {
                const term = this.documentObject.createElement("dt");
                term.textContent = headers[index]?.textContent?.trim() || `Поле ${index + 1}`;
                const definition = this.documentObject.createElement("dd");
                definition.textContent = value || "—";
                facts.append(term, definition);
            });
            const list = this.documentObject.createElement("div");
            list.className = "mc-action-dialog-list";
            const refresh = this.documentObject.createElement("button");
            refresh.type = "button";
            refresh.className = "mc-action-dialog-item";
            const refreshTitle = this.documentObject.createElement("strong");
            const proposed = values[values.length - 1];
            const passiveRecommendation = /^(ждать|система|нет действий|готово|блок)/i.test(proposed || "");
            refreshTitle.textContent = proposed && proposed !== "Нет данных" && proposed !== "—" && !passiveRecommendation
                ? proposed : "Проверить сейчас";
            const refreshDetail = this.documentObject.createElement("span");
            refreshDetail.textContent = "Обновить источник, связи и рекомендации без ослабления критериев PASS";
            refresh.append(refreshTitle, refreshDetail);
            refresh.addEventListener("click", async () => {
                refresh.disabled = true;
                dialog.close();
                dialog.remove();
                this.setRowStatus(row, "Выполняется", 50, "RUNNING");
                try {
                    await this.actionSink({
                        actionId:"research.request.refresh", actionKind:"COMMAND", interactionKind:"DOUBLE_CLICK",
                        targetId:table.dataset.mcNodeId || row.dataset.mcNodeId || "TABLE_REVIEW",
                        commandCode:"RESEARCH.REQUEST_REFRESH", policyClass:"RESEARCH_MAINTENANCE",
                        requiresApproval:false, reversible:true,
                        rollbackCode:"RESEARCH.CANCEL_PENDING_REQUEST", idempotencyKey:"client.request"
                    });
                    this.setRowStatus(row, "Ожидает", 10, "WARNING");
                    this.announce("Перепроверка поставлена в очередь", "SUCCESS");
                } catch (error) {
                    this.setRowStatus(row, "Ошибка", 0, "FAIL");
                    this.announce("Не удалось поставить перепроверку в очередь", "ERROR");
                }
            });
            list.appendChild(refresh);
            const keep = this.documentObject.createElement("button");
            keep.type = "button";
            keep.className = "mc-action-dialog-item";
            const keepTitle = this.documentObject.createElement("strong");
            keepTitle.textContent = "Оставить без изменений";
            const keepDetail = this.documentObject.createElement("span");
            keepDetail.textContent = "Закрыть окно и сохранить текущее решение";
            keep.append(keepTitle, keepDetail);
            keep.addEventListener("click", () => { dialog.close(); dialog.remove(); });
            list.appendChild(keep);
            const close = this.documentObject.createElement("button");
            close.type = "button";
            close.className = "mc-action-dialog-close";
            close.textContent = "Закрыть";
            close.addEventListener("click", () => dialog.close());
            dialog.addEventListener("close", () => dialog.remove());
            dialog.append(title, hint, facts, list, close);
            this.documentObject.body.appendChild(dialog);
            this.showActionDialog(dialog);
        }

        openRecommendedActions(sourceElement) {
            const table = sourceElement.closest("table");
            if (!table) return;
            if (
                sourceElement.dataset.mcActionKind === "NAVIGATE"
                || (sourceElement.dataset.mcNodeId || "").startsWith("control.section.funnel.row.")
            ) {
                this.openFunnelActions(sourceElement);
                return;
            }
            const requiresOperator = (row) => Boolean(row.dataset.mcActionId)
                && !row.hasAttribute("disabled");
            if (!requiresOperator(sourceElement)) {
                this.openRowResolution(sourceElement);
                return;
            }
            const rows = [sourceElement];
            if (!rows.length) return;

            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "recommended");
            const title = this.documentObject.createElement("h2");
            title.textContent = "Рекомендуемые действия";
            const hint = this.documentObject.createElement("p");
            hint.textContent = "Выбранное действие будет поставлено в очередь.";
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
                    : row.dataset.mcActionId === "operator.decision.refresh"
                        ? "Обновить решение"
                        : "Принять рекомендацию";
                const itemTitle = this.documentObject.createElement("strong");
                itemTitle.textContent = `${priority}. ${commandLabel}`;
                const itemReason = this.documentObject.createElement("span");
                itemReason.textContent = `${action}: ${reason}`;
                item.append(itemTitle, itemReason);
                item.addEventListener("click", async () => {
                    item.disabled = true;
                    dialog.close();
                    dialog.remove();
                    this.setRowStatus(row, "Выполняется", 50, "RUNNING");
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
                        this.setRowStatus(row, "Ожидает", 10, "WARNING");
                        this.announce("Заявка принята и ожидает выполнения", "SUCCESS");
                    } catch (error) {
                        this.setRowStatus(row, "Ошибка", 0, "FAIL");
                        this.announce("Не удалось поставить заявку в очередь", "ERROR");
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
            this.showActionDialog(dialog);
        }

        openBlockActions(row) {
            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const values = Array.from(row.cells).map((cell) => cell.textContent.trim());
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "block-remediation");
            const title = this.documentObject.createElement("h2");
            title.textContent = `Блокировка: ${values[0] || "неизвестна"}`;
            const hint = this.documentObject.createElement("p");
            hint.textContent = "Прямой обход риск-контроля запрещён. Система перепроверит доказательства и снимет блок только при PASS.";
            const list = this.documentObject.createElement("div");
            list.className = "mc-action-dialog-list";
            const add = (label, detail, handler, disabled=false) => {
                const button=this.documentObject.createElement("button");
                button.type="button"; button.className="mc-action-dialog-item"; button.disabled=disabled;
                const strong=this.documentObject.createElement("strong"); strong.textContent=label;
                const span=this.documentObject.createElement("span"); span.textContent=detail;
                button.append(strong,span); button.addEventListener("click",handler); list.appendChild(button);
            };
            add(values[4] || "Проверить и снять блок", "Поставить аудируемую перепроверку в системную очередь", async () => {
                dialog.close(); dialog.remove();
                this.setRowStatus(row, "Выполняется", 50, "RUNNING");
                try {
                    await this.actionSink({
                        actionId:row.dataset.mcActionId,actionKind:row.dataset.mcActionKind,
                        interactionKind:"DOUBLE_CLICK",targetId:row.dataset.mcTargetId || null,
                        commandCode:row.dataset.mcCommandCode,policyClass:row.dataset.mcPolicyClass,
                        requiresApproval:false,reversible:true,
                        rollbackCode:row.dataset.mcRollbackCode,idempotencyKey:"client.request"
                    });
                    this.setRowStatus(row, "Ожидает", 10, "WARNING");
                    this.announce("Перепроверка блока поставлена в очередь", "SUCCESS");
                } catch (error) {
                    this.setRowStatus(row, "Ошибка", 0, "FAIL");
                    this.announce("Не удалось поставить перепроверку блока", "ERROR");
                }
            });
            add("Оставить блок", "Не менять ограничение до появления новых доказательств", () => {
                dialog.close(); dialog.remove();
            });
            add("Другое решение", "Открыть поиск edge и изменить исследовательский сценарий", () => {
                dialog.close(); dialog.remove();
                globalObject.location.href="/workspace-v2/research";
            });
            const close=this.documentObject.createElement("button");
            close.type="button"; close.className="mc-action-dialog-close"; close.textContent="Закрыть";
            close.addEventListener("click",()=>dialog.close());
            dialog.addEventListener("close",()=>dialog.remove());
            dialog.append(title,hint,list,close); this.documentObject.body.appendChild(dialog); this.showActionDialog(dialog);
        }

        openOperatorDetails(row) {
            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const values = Array.from(row.cells).map((cell) => cell.textContent.trim());
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "operator-details");
            const title = this.documentObject.createElement("h2");
            title.textContent = values[1] || "Решение оператора";
            const hint = this.documentObject.createElement("p");
            hint.textContent = "Строка доступна для просмотра; исполняемого действия сейчас нет.";
            const list = this.documentObject.createElement("dl");
            list.className = "mc-v2-values";
            [["Причина", values[2]], ["Эффект", values[3]], ["Статус", values[4]],
             ["Срок", values[5]], ["Далее", values[6]]].forEach(([label, value]) => {
                const key = this.documentObject.createElement("dt"); key.textContent = label;
                const content = this.documentObject.createElement("dd"); content.textContent = value || "—";
                list.append(key, content);
            });
            const actions = this.documentObject.createElement("div");
            actions.className = "mc-action-dialog-list";
            const refresh = this.documentObject.createElement("button");
            refresh.type = "button";
            refresh.className = "mc-action-dialog-item";
            const refreshTitle = this.documentObject.createElement("strong");
            refreshTitle.textContent = "Проверить сейчас";
            const refreshDetail = this.documentObject.createElement("span");
            refreshDetail.textContent = "Поставить обновление доказательств и решения в системную очередь";
            refresh.append(refreshTitle, refreshDetail);
            refresh.addEventListener("click", async () => {
                refresh.disabled = true;
                dialog.close(); dialog.remove();
                this.setRowStatus(row, "Выполняется", 50, "RUNNING");
                try {
                    await this.actionSink({
                        actionId:"research.request.refresh", actionKind:"COMMAND", interactionKind:"DOUBLE_CLICK",
                        targetId:row.dataset.mcNodeId || "OPERATOR_REVIEW",
                        commandCode:"RESEARCH.REQUEST_REFRESH", policyClass:"RESEARCH_MAINTENANCE",
                        requiresApproval:false, reversible:true,
                        rollbackCode:"RESEARCH.CANCEL_PENDING_REQUEST", idempotencyKey:"client.request"
                    });
                    this.setRowStatus(row, "Ожидает", 10, "WARNING");
                    this.announce("Проверка поставлена в очередь", "SUCCESS");
                } catch (error) {
                    this.setRowStatus(row, "Ошибка", 0, "FAIL");
                    this.announce("Не удалось поставить проверку в очередь", "ERROR");
                }
            });
            actions.appendChild(refresh);
            const close = this.documentObject.createElement("button");
            close.type = "button"; close.className = "mc-action-dialog-close"; close.textContent = "Закрыть";
            close.addEventListener("click", () => dialog.close());
            dialog.addEventListener("close", () => dialog.remove());
            const openSection = this.documentObject.createElement("button");
            openSection.type = "button"; openSection.className = "mc-action-dialog-item";
            const openTitle = this.documentObject.createElement("strong");
            openTitle.textContent = values[4]?.includes("Блок") ? "Открыть допуски" : "Открыть ответственный раздел";
            const openDetail = this.documentObject.createElement("span");
            openDetail.textContent = "Проверить источник, ограничения и следующий допустимый переход";
            openSection.append(openTitle, openDetail);
            openSection.addEventListener("click", () => {
                dialog.close(); dialog.remove();
                globalObject.location.href = "/workspace-v2/control-center/edge-oos";
            });
            actions.appendChild(openSection);
            dialog.append(title, hint, list, actions, close);
            this.documentObject.body.appendChild(dialog);
            this.showActionDialog(dialog);
        }

        openOperatorCardActions(card, emit) {
            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "operator-card");
            const title = this.documentObject.createElement("h2");
            title.textContent = card.querySelector("h2")?.textContent?.trim() || "Операторская функция";
            const texts = Array.from(card.querySelectorAll("p,dd")).map((item) => item.textContent.trim()).filter(Boolean);
            const hint = this.documentObject.createElement("p");
            hint.textContent = texts[0] || "Текущее состояние функции";
            const result = this.documentObject.createElement("p");
            result.textContent = texts[texts.length - 1] || "Нет данных";
            const actions = this.documentObject.createElement("div");
            actions.className = "mc-action-dialog-list";
            const open = this.documentObject.createElement("button");
            open.type = "button"; open.className = "mc-action-dialog-item";
            const openTitle = this.documentObject.createElement("strong"); openTitle.textContent = "Открыть раздел";
            const openDetail = this.documentObject.createElement("span"); openDetail.textContent = "Перейти к данным, причинам и доступным действиям";
            open.append(openTitle, openDetail);
            open.addEventListener("click", async () => {
                dialog.close(); dialog.remove();
                await this.activateInteractive(card, emit, "DOUBLE_CLICK", "Открываю раздел…");
            });
            actions.appendChild(open);
            const close = this.documentObject.createElement("button");
            close.type = "button"; close.className = "mc-action-dialog-close"; close.textContent = "Закрыть";
            close.addEventListener("click", () => dialog.close());
            dialog.addEventListener("close", () => dialog.remove());
            dialog.append(title, hint, result, actions, close);
            this.documentObject.body.appendChild(dialog);
            this.showActionDialog(dialog);
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
            const isCommand = row.dataset.mcActionKind === "COMMAND";
            openTitle.textContent = isCommand
                ? "Пересобрать связь стадий"
                : `Открыть этап «${stage}»`;
            const detail = this.documentObject.createElement("span");
            detail.textContent = isCommand
                ? "Поставить в БД обновление источников и канонических связей"
                : (recommendations[stage] || "Открыть ответственный режим и проверить причину статуса");
            open.append(openTitle, detail);
            open.addEventListener("click", async () => {
                open.disabled = true;
                dialog.close();
                if (isCommand) this.setRowStatus(row, "Выполняется", 50, "RUNNING");
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
                    if (isCommand) {
                        this.setRowStatus(row, "Ожидает", 10, "WARNING");
                        this.announce("Перепроверка связи поставлена в очередь", "SUCCESS");
                    }
                } catch (error) {
                    if (isCommand) this.setRowStatus(row, "Ошибка", 0, "FAIL");
                    this.announce("Не удалось поставить перепроверку в очередь", "ERROR");
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
            dialog.append(title, hint, list, actions, close);
            this.documentObject.body.appendChild(dialog);
            this.showActionDialog(dialog);
        }

        openSwingDetails(row) {
            this.documentObject.querySelector("[data-mc-action-dialog]")?.remove();
            const values = Array.from(row.cells).map((cell) => cell.textContent.trim());
            const labels = ["Приоритет","Инструмент","Алгоритм","Таймфрейм","Этап","Накоплено","Нужно","Прогресс","Статус","Позиция","Paper PnL","Риск"];
            const dialog = this.documentObject.createElement("dialog");
            dialog.setAttribute("data-mc-action-dialog", "swing");
            const title = this.documentObject.createElement("h2");
            title.textContent = `${values[1] || "Swing-кандидат"} · ${values[2] || "Алгоритм"}`;
            const hint = this.documentObject.createElement("p");
            hint.textContent = "Текущий автономный путь OOS → Forward → Shadow → Paper. LIVE отключён.";
            const list = this.documentObject.createElement("dl");
            list.className = "mc-v2-values";
            labels.forEach((label,index) => {
                const key = this.documentObject.createElement("dt"); key.textContent = label;
                const value = this.documentObject.createElement("dd"); value.textContent = values[index] || "—";
                list.append(key,value);
            });
            const close = this.documentObject.createElement("button");
            close.type="button"; close.className="mc-action-dialog-close"; close.textContent="Закрыть";
            close.addEventListener("click",()=>dialog.close());
            dialog.addEventListener("close",()=>dialog.remove());
            dialog.append(title,hint,list,close); this.documentObject.body.appendChild(dialog); this.showActionDialog(dialog);
        }

        beginDocument() {
            this.mountElement.replaceChildren();
            this.stack = [];
            this.nodesRendered = 0;
        }

        groupControlCenterSections() {
            const groups = [
                {code:"process",labelKey:"control.view.group.process",descriptionKey:"control.view.group.process.description",open:false,sections:[
                    "swing_lifecycle","edge_search_process","edge_search_results","forward_pass_process",
                    "forward_readiness","shadow_process","shadow_alerts","forward_blockers","shadow"]},
                {code:"funnel",labelKey:"control.view.group.funnel",descriptionKey:"control.view.group.funnel.description",open:false,sections:["funnel","loss_reasons"]},
                {code:"execution",labelKey:"control.view.group.execution",descriptionKey:"control.view.group.execution.description",open:false,sections:[
                    "execution","microstructure_priorities","execution_microstructure",
                    "execution_historical","market","shadow_requirements"]},
                {code:"methodology",labelKey:"control.view.group.methodology",descriptionKey:"control.view.group.methodology.description",open:false,sections:[
                    "volatility","risk","entry","exit","block","relationships"]}
            ];
            if (!this.translate) throw new Error("BROWSER_PLATFORM_DRIVER_V2_TRANSLATOR_REQUIRED");
            const t = (key,args={}) => this.translate(key,args,this.localeCode);
            const renderedGroups = [];
            groups.forEach((group) => {
                const sections = group.sections.map((code) =>
                    this.mountElement.querySelector(`[data-mc-node-id="control.section.${code}"]`)
                ).filter(Boolean);
                if (!sections.length) return;
                const parent = sections[0].parentElement;
                if (!parent) return;
                const details = this.documentObject.createElement("details");
                details.className = "mc-control-section-group";
                details.dataset.mcSectionGroup = group.code;
                details.open = group.open;
                const summary = this.documentObject.createElement("summary");
                const heading = this.documentObject.createElement("span");
                heading.className = "mc-control-group-heading";
                const label = this.documentObject.createElement("strong");
                label.textContent = t(group.labelKey);
                const description = this.documentObject.createElement("span");
                description.className = "mc-control-group-description";
                description.textContent = t(group.descriptionKey);
                const count = this.documentObject.createElement("span");
                count.className = "mc-control-group-count";
                const blocked = sections.reduce((total, section) => {
                    const explicit = section.querySelectorAll(
                        '[data-mc-status="BLOCKED"], [data-mc-status="FAIL"]'
                    ).length;
                    const restrictions = section.matches('[data-mc-node-id="control.section.block"]')
                        ? section.querySelectorAll('[data-mc-node="table_row"]').length
                        : 0;
                    return total + Math.max(explicit, restrictions);
                }, 0);
                count.textContent = t("control.view.group.count", {sections:sections.length, blocked});
                heading.append(label,description);
                summary.append(heading,count);
                parent.insertBefore(details,sections[0]);
                details.appendChild(summary);
                sections.forEach((section) => details.appendChild(section));
                renderedGroups.push({details,blocked});
            });
            if (!renderedGroups.length) return;
            const groupGrid = this.documentObject.createElement("div");
            groupGrid.className = "mc-control-group-grid";
            const groupParent = renderedGroups[0].details.parentElement;
            groupParent.insertBefore(groupGrid,renderedGroups[0].details);
            renderedGroups.forEach(({details}) => groupGrid.appendChild(details));
            let allowMultiple = false;
            renderedGroups.forEach(({details}) => {
                details.querySelector("summary").addEventListener("click", () => { allowMultiple=false; });
                details.addEventListener("toggle", () => {
                    if (!details.open || allowMultiple) return;
                    renderedGroups.forEach(({details:other}) => {
                        if (other !== details) other.open=false;
                    });
                });
            });
            const toolbar = this.documentObject.createElement("div");
            toolbar.className = "mc-control-view-toolbar";
            toolbar.setAttribute("role", "toolbar");
            toolbar.setAttribute("aria-label", t("control.view.toolbar.aria"));
            const addView = (code,labelKey,multiple,apply) => {
                const button = this.documentObject.createElement("button");
                button.type = "button";
                button.dataset.mcControlView = code;
                button.textContent = t(labelKey);
                button.addEventListener("click", () => {
                    allowMultiple = multiple;
                    apply();
                    toolbar.querySelectorAll("button").forEach((item) =>
                        item.setAttribute("aria-pressed", String(item === button)));
                });
                toolbar.appendChild(button);
            };
            addView("summary","control.view.summary",false,() => renderedGroups.forEach(({details}) => { details.open=false; }));
            addView("blocked","control.view.blocked",true,() => renderedGroups.forEach(({details,blocked}) => { details.open=blocked>0; }));
            addView("all","control.view.all",true,() => renderedGroups.forEach(({details}) => { details.open=true; }));
            toolbar.querySelector('[data-mc-control-view="summary"]').setAttribute("aria-pressed", "true");
            groupParent.insertBefore(toolbar,groupGrid);
        }

        renderNode(node, context) {
            let tagName = ELEMENT_BY_NODE_TYPE[node.type];
            if (node.type === "title" && node.content && node.content.level_code === "PAGE") tagName = "h1";
            const element = this.documentObject.createElement(tagName);
            element.setAttribute("data-mc-node", node.type);
            element.setAttribute("data-mc-node-id", node.node_id);
            if (node.content && node.content.column_code) {
                element.setAttribute("data-mc-column-code", String(node.content.column_code));
            }
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
                        const nodeId = element.getAttribute("data-mc-node-id") || "";
                        const isUniverseRow = /^research\.(?:universe\.\d+|scout\.[a-z_]+\.\d+)$/.test(nodeId);
                        if (nodeId.startsWith("research.scout."))
                            globalObject.setTimeout(()=>this.ensureScoutFilters(element),0);
                        element.addEventListener("click", (event) => {
                            const cell = event.target.closest && event.target.closest('[data-mc-node="table_cell"]');
                            if (isUniverseRow && cell?.getAttribute("data-mc-node-id")?.endsWith(".operator_action")) {
                                this.openUniverseActions(element); return;
                            }
                            this.selectInteractive(element,"Двойной клик — открыть рекомендуемые действия");
                        });
                        element.addEventListener("dblclick", (event) => {
                            const cell = event.target.closest && event.target.closest('[data-mc-node="table_cell"]');
                            const isResearchRow = nodeId.startsWith("research.audit.");
                            const isMethodologyRow = nodeId.startsWith("research.failures.");
                            const isSwingRow = nodeId.startsWith("control.section.swing_lifecycle.row.");
                            const isRecommendation = cell?.getAttribute("data-mc-node-id")?.endsWith(".recommendation");
                            const isBlockRow = nodeId.startsWith("control.section.block.row.");
                            if (isBlockRow) this.openBlockActions(element);
                            else if (isMethodologyRow) this.openMethodologyActions(element);
                            else if (isSwingRow) this.openSwingDetails(element);
                            else if (isUniverseRow) this.openUniverseActions(element);
                            else if (isResearchRow && isRecommendation) this.openResearchActions(element);
                            else if (isResearchRow) this.announce("Запуск доступен двойным кликом в колонке «Далее»");
                            else this.openRecommendedActions(element);
                        });
                    } else if (isContainer) {
                        element.addEventListener("click", () => this.selectInteractive(element,"Двойной клик — открыть раздел"));
                        element.addEventListener("dblclick", () => node.node_id.startsWith("home.operator.")
                            ? this.openOperatorCardActions(element,emit)
                            : this.activateInteractive(element,emit,"DOUBLE_CLICK","Открываю раздел…"));
                    } else if (isCommandButton) {
                        element.addEventListener("click", () => this.selectInteractive(element,"Двойной клик — выполнить действие"));
                        element.addEventListener("dblclick", async () => {
                            await this.activateInteractive(element,emit,"DOUBLE_CLICK","Выполняю действие…");
                        });
                    } else {
                        element.addEventListener("click", () => emit("CLICK"));
                    }
                    element.addEventListener("keydown", (event) => {
                        if (event.key === "Enter" || (!requiresDoubleClick && event.key === " ")) {
                            event.preventDefault();
                            if (isTableRow) this.openRecommendedActions(element);
                            else if (isContainer && node.node_id.startsWith("home.operator.")) this.openOperatorCardActions(element,emit);
                            else if (isContainer) this.activateInteractive(element,emit,"DOUBLE_CLICK","Открываю раздел…");
                            else if (isCommandButton) this.activateInteractive(element,emit,"DOUBLE_CLICK","Выполняю действие…");
                            else emit("CLICK");
                        }
                    });
                }
            }
            if (!node.action && node.type === "table_row" && node.node_id.startsWith("home.operator.action.")) {
                element.setAttribute("role", "button");
                element.setAttribute("tabindex", "0");
                element.setAttribute("data-mc-interaction", "double-click");
                element.setAttribute("title", "Двойной клик — посмотреть решение");
                element.addEventListener("click", () => this.selectInteractive(element,"Двойной клик — посмотреть решение"));
                element.addEventListener("dblclick", () => this.openOperatorDetails(element));
                element.addEventListener("keydown", (event) => {
                    if (event.key === "Enter") { event.preventDefault(); this.openOperatorDetails(element); }
                });
            } else if (!node.action && node.type === "card" && node.node_id.startsWith("research.tile.")) {
                element.setAttribute("role", "button");
                element.setAttribute("tabindex", "0");
                element.setAttribute("data-mc-interaction", "double-click");
                element.setAttribute("title", "Двойной клик — пояснение и рекомендуемые действия");
                element.addEventListener("click", () => this.selectInteractive(element, "Двойной клик — открыть рекомендуемые действия"));
                element.addEventListener("dblclick", () => this.openGovernanceActions(element));
                element.addEventListener("keydown", (event) => {
                    if (event.key === "Enter") { event.preventDefault(); this.openGovernanceActions(element); }
                });
            } else if (
                !node.action
                && node.type === "table_row"
                && !(node.children || []).some((child) => child.type === "table_header_cell")
            ) {
                element.setAttribute("role", "button");
                element.setAttribute("tabindex", "0");
                element.setAttribute("data-mc-interaction", "double-click");
                element.setAttribute("title", "Двойной клик — открыть решение");
                const openStaticResolution = () => {
                    if (node.node_id.startsWith("research.failures.")) this.openMethodologyActions(element);
                    else if (node.node_id.startsWith("control.section.swing_lifecycle.row.")) this.openSwingDetails(element);
                    else this.openRowResolution(element);
                };
                element.addEventListener("click", () => this.selectInteractive(element, "Двойной клик — открыть решение"));
                element.addEventListener("dblclick", openStaticResolution);
                element.addEventListener("keydown", (event) => {
                    if (event.key === "Enter") { event.preventDefault(); openStaticResolution(); }
                });
            }
            if (context.displayValue !== null && context.displayValue !== undefined) {
                element.textContent = String(context.displayValue);
            }
            if (context.tooltipValue) {
                element.setAttribute("title", String(context.tooltipValue));
                element.setAttribute("aria-label", `${String(context.displayValue || "")}. ${String(context.tooltipValue)}`);
            }
            if (node.type === "table_header_cell") {
                const hint = this.localized("table.sort.hint", "Двойной клик — сортировать");
                const currentTitle = element.getAttribute("title");
                element.setAttribute("title", currentTitle ? `${currentTitle}. ${hint}` : hint);
                element.setAttribute("tabindex", "0");
                element.setAttribute("aria-sort", "none");
                element.addEventListener("dblclick", (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    this.sortTable(element);
                });
                element.addEventListener("keydown", (event) => {
                    if (event.key === "Enter") {
                        event.preventDefault();
                        this.sortTable(element);
                    }
                });
            }
            if (node.type === "table_cell" && node.node_id.endsWith(".recommendation") && node.content?.message_args) {
                element.dataset.mcProcessId = String(node.content.message_args.process_id || "");
                element.dataset.mcActions = JSON.stringify(node.content.message_args.actions || []);
            }
            if (node.type === "table_cell" && node.content && node.content.column_code === "status") {
                const label = String(context.displayValue || "");
                const progressByLabel = {
                    "Требуется решение оператора": 10,
                    "Принято к рассмотрению": 50,
                    "Результат измерен": 100,
                    "Измерение": 50,
                    "Измерить": 75,
                    "Улучшение": 100,
                    "Без эффекта": 100,
                    "Ухудшение": 100,
                    "Устарело": 0,
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
            this.restoreTableSorts();
            this.groupControlCenterSections();
            return Object.freeze({driverVersion: DRIVER_VERSION, nodesRendered: this.nodesRendered});
        }
    }

    globalObject.MarketCoreBrowserPlatformDriverV2 = Object.freeze({
        driverVersion: DRIVER_VERSION,
        Driver: BrowserPlatformDriverV2
    });
})(globalThis);
