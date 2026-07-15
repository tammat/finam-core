from pathlib import Path


def test_home_cards_use_named_navigation_without_execution_coupling() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py"
    ).read_text()
    assert "home.decision.open_named" in source
    assert '"method":' not in source


def test_dom_driver_performs_real_navigation_without_posting() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src/marketcore/presentation/ui_runtime/assets/v1/browser_dom_driver_v1.js"
    ).read_text()
    assert "globalObject.location.assign" in source
    assert "globalObject.fetch" not in source
    assert "runtime.css" not in source
