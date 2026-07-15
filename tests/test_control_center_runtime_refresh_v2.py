from pathlib import Path


def test_control_center_runtime_refreshes_without_overlapping_requests() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src/marketcore/presentation/ui_runtime/assets/v1/control_center_runtime_v2.js"
    ).read_text(encoding="utf-8")

    assert "REFRESH_INTERVAL_MS = 30000" in source
    assert "refreshInProgress" in source
    assert "document.hidden" in source
    assert "setInterval(refresh, REFRESH_INTERVAL_MS)" in source
    assert 'addEventListener("visibilitychange", refresh)' in source
    assert 'cache: "no-store"' in source


def test_control_center_routes_open_their_real_sections() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src/marketcore/presentation/ui_runtime/assets/v1/control_center_runtime_v2.js"
    ).read_text(encoding="utf-8")
    for route, section in (
        ("data-quality", "market-prerequisites"),
        ("signal-funnel", "signal-funnel"),
        ("execution-edge", "execution-quality"),
        ("failure-diagnostics", "block-analysis"),
    ):
        assert f'"{route}": "{section}"' in source
    assert 'section.scrollIntoView({block: "start"})' in source
    assert 'section.setAttribute("data-active-route", "true")' in source
