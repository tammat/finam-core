from pathlib import Path


def test_all_double_click_targets_explain_the_interaction() -> None:
    driver=Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert 'data-mc-interaction", "double-click"' in driver
    assert "Двойной клик — открыть раздел" in driver
    assert "Двойной клик — открыть рекомендуемые действия" in driver
    assert "Двойной клик — выполнить после подтверждения" in driver


def test_first_click_selects_and_double_click_activates_with_feedback() -> None:
    driver=Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    css=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert "selectInteractive(element" in driver
    assert "activateInteractive(element" in driver
    assert "Открываю раздел…" in driver
    assert "Не удалось выполнить действие" in driver
    assert '[data-mc-ux-toast]' in css
    assert '[data-mc-selected="true"]' in css


def test_asset_versions_force_safari_to_load_fixed_handlers() -> None:
    shell=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html").read_text()
    assert "browser-platform-driver.js?v=20260717.2" in shell
    assert "workspace.css?v=20260717.9" in shell
