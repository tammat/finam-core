from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js"
CSS = ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css"


def test_navigation_exposes_loading_and_failure_states() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert 'setAttribute("data-runtime-status", "LOADING")' in source
    assert 'setAttribute("aria-busy", "true")' in source
    assert 'setAttribute("data-runtime-status", "FAILED")' in source
    assert 'removeAttribute("aria-busy")' in source


def test_loading_state_uses_i18n_label() -> None:
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'services.translate("workspace.loading"' in bootstrap
    assert '[data-runtime-status="LOADING"]::after' in css
    assert "content: attr(data-loading-label)" in css
