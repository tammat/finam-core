from pathlib import Path


def test_back_button_is_always_present_in_shell() -> None:
    shell=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html").read_text()
    assert 'id="marketcore-workspace-back"' in shell
    assert 'id="marketcore-workspace-back" type="button" hidden' not in shell


def test_direct_nested_url_returns_home_without_navigation_history() -> None:
    source=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js").read_text()
    assert 'previousTargetId || "container.home"' in source
    assert 'currentTargetId === "container.home"' in source
    assert 'backButton.hidden = false' in source
    assert 'backButton.disabled = atHome' in source


def test_back_button_asset_cache_is_invalidated() -> None:
    shell=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html").read_text()
    assert "workspace-shell-bootstrap.js?v=20260717.4" in shell
    assert "workspace.css?v=20260717.9" in shell
