from pathlib import Path


def test_double_click_opens_prioritized_operator_action_dialog() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert "openRecommendedActions(sourceElement)" in source
    assert 'Boolean(row.dataset.mcActionId)' in source
    assert "this.openOperatorDetails(sourceElement)" in source
    assert "const rows = [sourceElement];" in source
    assert 'else this.openRecommendedActions(element);' in source
    assert '"Принять рекомендацию"' in source
    assert '"Проверить результат"' in source


def test_operator_choice_is_the_confirmation_and_dialog_is_removed() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    handler = source.split('item.addEventListener("click", async () => {', 1)[1].split("list.appendChild(item);", 1)[0]
    assert "globalObject.confirm" not in handler
    assert "dialog.close();" in handler
    assert "dialog.remove();" in handler


def test_research_dialog_closes_immediately_after_confirmation() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    handler = source.split('if (!globalObject.confirm(`Подтвердить: ${option.label}?`)) return;', 1)[1]
    before_request = handler.split("await this.actionSink", 1)[0]
    assert "dialog.close();" in before_request
    assert "dialog.remove();" in before_request


def test_verdict_progress_tracks_operator_decision_state() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert 'node.node_id.endsWith(".status")' in source
    assert 'this.documentObject.createElement("progress")' in source
    assert '"Принято к рассмотрению": 50' in source
    assert '"Результат измерен": 100' in source
    assert 'row.setAttribute("data-mc-operator-required", "true")' in source


def test_operator_action_dialog_has_runtime_styles() -> None:
    css = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert 'dialog[data-mc-action-dialog]' in css
    assert 'td[data-mc-node-id$=".status"] progress' in css


def test_non_executable_operator_rows_remain_readable() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert "openOperatorDetails(row)" in source
    assert 'node.node_id.startsWith("home.operator.action.")' in source
    assert 'element.addEventListener("dblclick", () => this.openOperatorDetails(element));' in source
