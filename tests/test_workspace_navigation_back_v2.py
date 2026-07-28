from pathlib import Path


def test_workspace_uses_sidebar_and_browser_history_without_duplicate_buttons() -> None:
    shell = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html").read_text()
    bootstrap = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js").read_text()
    assert 'id="marketcore-workspace-back"' not in shell
    assert 'id="marketcore-workspace-home"' not in shell
    assert "navigationStack.push(currentTargetId)" in bootstrap
    assert 'globalObject.addEventListener("popstate"' in bootstrap
    assert 'workspace.menu.home' in bootstrap


def test_actionable_containers_have_strong_hover_feedback() -> None:
    css = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert 'article[role="link"][data-mc-action-id]:hover' in css
    assert "filter: brightness(1.12)" in css
    assert "translateY(-3px)" in css
