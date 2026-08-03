from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js"


def test_every_panel_preserves_interaction_state_during_refresh() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert "capturePanelState" in source
    assert "restorePanelState" in source
    assert 'render(currentEndpoint, {preserveState: true})' in source
    assert "scrollX" in source
    assert "scrollY" in source
    assert "data-mc-section-group" in source
    assert "data-mc-scout-filter" in source
    assert "focused" in source


def test_panel_state_survives_full_page_reload_and_navigation() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert "sessionStorage.setItem(panelStateStorageKey()" in source
    assert "sessionStorage.getItem(panelStateStorageKey()" in source
    assert 'addEventListener("pagehide", () => persistPanelState())' in source
    assert "{restoreStored: true}" in source


def test_manual_reload_starts_at_top_without_losing_panel_controls() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert 'history.scrollRestoration = "manual"' in source
    assert "{restoreStored: true, restorePageScroll: false}" in source
    assert "restorePageScroll: options.restorePageScroll !== false" in source


def test_refresh_timer_is_single_and_does_not_reset_research_twice() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert "researchRefreshTimer" not in source
    assert source.count("globalObject.setInterval(refreshVisiblePanel") == 1
    assert '"container.home"' in source
    assert "AUTO_REFRESH_TARGETS.has(currentTargetId)" in source
    assert "AUTO_REFRESH_INTERVAL_MS = 10000" in source
    assert 'addEventListener("visibilitychange"' in source
