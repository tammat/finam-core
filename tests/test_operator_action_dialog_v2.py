from pathlib import Path


def test_double_click_opens_prioritized_operator_action_dialog() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert "openRecommendedActions(sourceElement)" in source
    assert 'cell.textContent.trim() === "Требуется решение оператора"' in source
    assert ".filter(requiresOperator)" in source
    assert ".sort((left, right) => Number(left.cells[0]?.textContent" in source
    assert 'element.addEventListener("dblclick", () => this.openRecommendedActions(element));' in source
    assert "globalObject.confirm" in source


def test_confidence_progress_is_limited_to_operator_decisions() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert 'node.node_id.endsWith(".confidence")' in source
    assert 'this.documentObject.createElement("progress")' in source
    assert 'row.setAttribute("data-mc-operator-required", "true")' in source
    assert "if (confidence && label) confidence.textContent = label" in source


def test_operator_action_dialog_has_runtime_styles() -> None:
    css = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert 'dialog[data-mc-action-dialog]' in css
    assert 'td[data-mc-node-id$=".confidence"] progress' in css
