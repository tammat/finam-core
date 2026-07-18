from pathlib import Path


def test_shell_always_contains_separate_back_and_home_buttons() -> None:
    shell=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html").read_text()
    assert 'id="marketcore-workspace-back"' in shell
    assert 'id="marketcore-workspace-home"' in shell
    assert "⌂ Домой" in shell


def test_home_button_clears_history_and_opens_home() -> None:
    source=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js").read_text()
    assert 'getElementById("marketcore-workspace-home")' in source
    assert "navigationStack.length = 0" in source
    assert 'currentTargetId = "container.home"' in source
    assert "homeButton.disabled = false" in source
    assert 'if (currentTargetId === "container.home") return' not in source


def test_home_button_assets_are_cache_busted() -> None:
    shell=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html").read_text()
    assert "workspace-shell-bootstrap.js?v=20260718.1" in shell
    assert "workspace.css?v=20260717.11" in shell
