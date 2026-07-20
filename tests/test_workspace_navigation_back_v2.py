from pathlib import Path


def test_workspace_has_visible_back_navigation() -> None:
    shell = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html").read_text()
    bootstrap = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js").read_text()
    css = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert 'id="marketcore-workspace-back"' in shell
    assert "navigationStack.push(currentTargetId)" in bootstrap
    assert 'backButton.addEventListener("click"' in bootstrap
    assert "await render(ENDPOINT_BY_TARGET[currentTargetId], {restoreStored: true})" in bootstrap
    assert "#marketcore-workspace-back:hover" in css


def test_actionable_containers_have_strong_hover_feedback() -> None:
    css = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert 'article[role="link"][data-mc-action-id]:hover' in css
    assert "filter: brightness(1.12)" in css
    assert "translateY(-3px)" in css
