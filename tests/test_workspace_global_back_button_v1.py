from pathlib import Path


def test_back_button_is_not_duplicated_outside_browser_history() -> None:
    shell=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html").read_text()
    assert 'id="marketcore-workspace-back"' not in shell


def test_direct_nested_url_returns_home_without_navigation_history() -> None:
    source=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js").read_text()
    assert 'globalObject.addEventListener("popstate"' in source
    assert 'initialTarget(globalObject.location.pathname)' in source


def test_back_button_asset_cache_is_invalidated() -> None:
    shell=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html").read_text()
    assert "workspace-shell-bootstrap.js?v=" in shell
    assert "workspace.css?v=" in shell
