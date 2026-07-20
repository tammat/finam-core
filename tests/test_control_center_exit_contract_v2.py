from pathlib import Path


def test_exit_section_uses_active_contract_even_without_current_observations() -> None:
    source = Path(
        "src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py"
    ).read_text(encoding="utf-8")
    assert "FROM analytics.research_entry_exit_contract_v1" in source
    assert "WHERE enabled" in source
    assert "LEFT JOIN current_observations" in source
    assert "AWAITING_OOS_EXIT_OBSERVATIONS" in source
    assert "exit_max_holding_bars" in source
    assert "exit_stop_atr" in source
    assert "exit_trail_atr" in source


def test_exit_contract_labels_and_statuses_are_db_driven() -> None:
    migration = Path(
        "sql/presentation/165_control_center_exit_contract_i18n_v1.sql"
    ).read_text(encoding="utf-8")
    for key in (
        "column.max.holding.bars",
        "column.minimum.bars",
        "column.stop.atr",
        "column.trail.atr",
        "column.trend.lookback",
        "status.dynamic_exit_v1",
        "status.fixed_hold",
        "status.awaiting_oos_exit_observations",
        "status.awaiting_closed_trades",
        "status.evaluated",
        "status.trend_down",
    ):
        assert key in migration

    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py"
    ).read_text(encoding="utf-8")
    assert '"scope_code"' in renderer
