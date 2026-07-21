from pathlib import Path


def test_shell_does_not_duplicate_sidebar_navigation() -> None:
    shell=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html").read_text()
    assert 'id="marketcore-workspace-back"' not in shell
    assert 'id="marketcore-workspace-home"' not in shell


def test_sidebar_home_opens_home_target() -> None:
    source=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js").read_text()
    assert '["container.home", "workspace.menu.home"]' in source
    assert "navigateToTarget(targetId)" in source


def test_home_button_assets_are_cache_busted() -> None:
    shell=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html").read_text()
    assert "workspace-shell-bootstrap.js?v=" in shell
    assert "workspace.css?v=" in shell
