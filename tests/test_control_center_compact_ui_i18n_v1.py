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


def test_active_compact_control_exposes_swing_pipeline_status() -> None:
    resolver = Path(
        "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py"
    ).read_text(encoding="utf-8")
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py"
    ).read_text(encoding="utf-8")
    assert "swing_future_data_readiness_v1" in resolver
    assert '"swing_summary": swing_summary' in resolver
    for label in ("Swing · путь к Paper", "Готовы к OOS", "Зависли", "Устаревшие данные"):
        assert label in renderer


def test_active_compact_control_explains_missing_edge() -> None:
    resolver = Path(
        "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py"
    ).read_text(encoding="utf-8")
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py"
    ).read_text(encoding="utf-8")
    assert "TIME_SHIFTED_ENTRY_V2" in resolver
    assert '"edge_diagnostics": edge_diagnostics' in resolver
    assert "Почему сигнал не создаёт edge" in renderer
    assert "Проверить условие входа; выходы пока не оптимизировать" in renderer
    assert "Gross → costs → Net" in renderer
    assert "COSTS_CONSUME_EDGE" in resolver
