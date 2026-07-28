from pathlib import Path
from types import SimpleNamespace

from marketcore.presentation.app import MarketCoreUiHandler


def test_rows_and_clickable_containers_require_double_click() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert 'const isTableRow = node.type === "table_row";' in source
    assert 'const isContainer = node.type === "card";' in source
    assert "const requiresDoubleClick = isTableRow || isContainer || isCommandButton;" in source
    assert 'if (isResearchRow && isRecommendation) this.openResearchActions(element);' in source
    assert 'else this.openRecommendedActions(element);' in source
    assert 'element.addEventListener("dblclick", () => node.node_id.startsWith("home.operator.")' in source
    assert '? this.openOperatorCardActions(element,emit)' in source
    assert 'if (isTableRow) this.openRecommendedActions(element);' in source
    assert 'else if (isContainer && node.node_id.startsWith("home.operator.")) this.openOperatorCardActions(element,emit);' in source
    assert 'else if (isContainer) this.activateInteractive(element,emit,"DOUBLE_CLICK","Открываю раздел…");' in source
    assert 'else emit("CLICK");' in source


def test_governance_tiles_open_recommended_actions_on_double_click() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert "openGovernanceActions(card)" in source
    assert 'node.node_id.startsWith("research.tile.")' in source
    assert 'element.addEventListener("dblclick", () => this.openGovernanceActions(element));' in source
    assert 'commandCode: refreshOnly.has(code) ? "RESEARCH.REQUEST_REFRESH" : "RESEARCH.RUN_EDGE_SEARCH"' in source
    assert 'interactionKind: "DOUBLE_CLICK"' in source


def test_action_controller_can_create_uuid_on_insecure_http_origin() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_action_controller_v2.js").read_text()
    assert 'typeof globalObject.crypto.randomUUID === "function"' in source
    assert "globalObject.crypto.getRandomValues(bytes)" in source
    assert "globalObject.Math.random()" in source
    assert "bytes[6] = (bytes[6] & 0x0f) | 0x40" in source
    assert "bytes[8] = (bytes[8] & 0x3f) | 0x80" in source


def test_same_origin_action_accepts_webview_without_fetch_metadata() -> None:
    request = SimpleNamespace(
        headers={"Host": "onezh.ddns.net:8080", "Origin": "http://onezh.ddns.net:8080"},
        client_address=("192.0.2.10", 12345),
    )
    assert MarketCoreUiHandler._is_same_origin_action_request(request)


def test_action_origin_must_still_match_host() -> None:
    request = SimpleNamespace(
        headers={"Host": "onezh.ddns.net:8080", "Origin": "https://attacker.example"},
        client_address=("192.0.2.10", 12345),
    )
    assert not MarketCoreUiHandler._is_same_origin_action_request(request)
def test_clickable_cards_highlight_and_open_only_on_double_click() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    css = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert 'const isContainer = node.type === "card"' in source
    assert 'this.openOperatorCardActions(element,emit)' in source
    assert 'this.activateInteractive(element,emit,"DOUBLE_CLICK","Открываю раздел…")' in source
    assert '[data-mc-node="card"][data-mc-action-id]:not([disabled]):hover' in css
    assert 'cursor: pointer' in css


def test_command_buttons_execute_on_double_click_without_second_confirmation() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert 'const isCommandButton = node.type === "action"' in source
    assert 'isTableRow || isContainer || isCommandButton' in source
    assert 'globalObject.confirm("Подтвердить выполнение действия?")' not in source
    assert 'activateInteractive(element,emit,"DOUBLE_CLICK","Выполняю действие…")' in source


def test_all_action_dialogs_use_double_click_and_have_no_close_button() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert "showActionDialog(dialog)" in source
    assert 'dialog.addEventListener("dblclick", (event) =>' in source
    assert 'action.dataset.mcDoubleClickActivation = "true"' in source
    assert 'dialog.querySelectorAll(".mc-action-dialog-close").forEach((button) => button.remove())' in source
    assert "if (event.target === dialog)" in source


def test_control_center_tables_are_grouped_under_collapsible_sections() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert "groupControlCenterSections" in source
    assert 'code:"process"' in source
    assert 'code:"funnel"' in source
    assert 'code:"execution"' in source
    assert 'code:"methodology"' in source
    assert 'details.className = "mc-control-section-group"' in source
    assert 'descriptionKey:"control.view.group.process.description"' in source
    assert 'groupGrid.className = "mc-control-group-grid"' in source
    assert 'section.matches(\'[data-mc-node-id="control.section.block"]\')' in source
    assert '"microstructure_priorities","execution_microstructure"' in source
    assert 'addView("summary","control.view.summary"' in source
    assert 'addView("blocked","control.view.blocked"' in source
    assert 'addView("all","control.view.all"' in source
    assert 'labelKey:"control.view.group.process"' in source
    assert 't("control.view.group.count"' in source
    assert 'data-mc-control-view="summary"' in source


def test_control_center_group_state_survives_auto_refresh_races() -> None:
    source = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js"
    ).read_text()
    assert 'mountElement.addEventListener("toggle"' in source
    assert "storedPanelState() || panelState" in source
    assert 'details[data-mc-section-group]' in source
    assert "const backgroundRefresh = Boolean(options.preserveState" in source
    assert 'if (!backgroundRefresh) {' in source


def test_executable_double_click_updates_status_until_database_refresh() -> None:
    source = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js"
    ).read_text()
    assert "setRowStatus(row, label, progressValue, statusCode)" in source
    assert 'this.setRowStatus(row, "Выполняется", 50, "RUNNING")' in source
    assert 'this.setRowStatus(row, "Ожидает", 10, "WARNING")' in source
    assert 'this.setRowStatus(row, "Ошибка", 0, "FAIL")' in source
    assert 'data-mc-column-code' in source


def test_table_headers_sort_on_double_click_and_survive_auto_refresh() -> None:
    source = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js"
    ).read_text()
    css = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css"
    ).read_text()
    migration = Path("sql/presentation/177_research_process_priority_i18n_v1.sql").read_text()
    assert "sortTable(header, requestedDirection = null, persist = true)" in source
    assert 'element.addEventListener("dblclick", (event) =>' in source
    assert "sortableValue(cell)" in source
    assert "restoreTableSorts()" in source
    assert "sessionStorage.setItem(this.tableSortKey(table)" in source
    assert 'data-mc-sort-direction="ascending"' in css
    assert 'data-mc-sort-direction="descending"' in css
    assert "table.sort.hint" in migration


def test_every_table_row_has_a_database_backed_resolution_dialog() -> None:
    source = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js"
    ).read_text()
    assert "openRowResolution(row)" in source
    assert 'actionId:"research.request.refresh"' in source
    assert 'commandCode:"RESEARCH.REQUEST_REFRESH"' in source
    assert "Исполняемая команда будет записана в БД" in source
    assert '&& node.type === "table_row"' in source
    assert "openStaticResolution" in source
