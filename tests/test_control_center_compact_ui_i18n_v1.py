from pathlib import Path


def test_live_session_codes_cannot_break_the_whole_control_center() -> None:
    migration = Path(
        "sql/presentation/164_control_center_compact_ui_i18n_v1.sql"
    ).read_text(encoding="utf-8")
    assert "status.europe_overlap" in migration
    assert "status.outside_session" in migration
    assert "status.volatility_scaled_momentum_v1" in migration
    assert "status.ema_trend_filter_v1" in migration
    assert "status.quote_matched" in migration
    assert "control.view.group.process" in migration
    assert "control.view.group.funnel" in migration
    assert "control.view.group.execution" in migration
    assert "control.view.group.methodology" in migration
    assert "control.view.group.count" in migration
    assert "control.view.toolbar.aria" in migration
    assert "control.view.summary" in migration
    assert "control.view.blocked" in migration
    assert "control.view.all" in migration


def test_compact_view_labels_are_not_hardcoded_in_platform_driver() -> None:
    source = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js"
    ).read_text(encoding="utf-8")
    for literal in ("Главное", "Только блоки", "Все детали", "Управление подробностями"):
        assert literal not in source
