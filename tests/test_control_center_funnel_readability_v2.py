from pathlib import Path


def test_funnel_uses_readable_source_and_conversion_i18n() -> None:
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py"
    ).read_text(encoding="utf-8")
    migration = Path(
        "sql/analytics/176_profit_funnel_readable_sources_i18n_v1.sql"
    ).read_text(encoding="utf-8")

    assert 'message_key = f"funnel.source.{_message_code(raw_value)}"' in renderer
    assert 'message_args = {"tooltip_value": raw_value}' in renderer
    assert 'message_key = f"funnel.conversion.{reason_code}"' in renderer
    assert "funnel.source.analytics.edge_discovery_run_v1.latest_done" in migration
    assert "funnel.source.public.orders.exchange_accepted" in migration
    assert "funnel.conversion.initial_stage" in migration
    assert "funnel.conversion.no_real_execution" in migration


def test_runtime_supports_auditable_literal_tooltips() -> None:
    runtime = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/domain_render_tree_runtime_v2.js"
    ).read_text(encoding="utf-8")
    assert "content.message_args.tooltip_value" in runtime
    assert "tooltipValue = String(content.message_args.tooltip_value)" in runtime


def test_progress_uses_blue_workspace_action_colour() -> None:
    css = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css"
    ).read_text(encoding="utf-8")
    assert "accent-color: var(--mc-action, #2d73a5)" in css
    assert "progress::-webkit-progress-value { background: var(--mc-action); }" in css
    assert "progress::-moz-progress-bar { background: var(--mc-action); }" in css


def test_missing_funnel_link_can_queue_a_database_refresh() -> None:
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py"
    ).read_text(encoding="utf-8")
    driver = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js"
    ).read_text(encoding="utf-8")
    cycle = Path(
        "src/scripts/run_market_universe_research_queue_cycle_v1.py"
    ).read_text(encoding="utf-8")
    resolver = Path(
        "src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py"
    ).read_text(encoding="utf-8")

    assert 'row.get("pass_rate_pct") is None and reason_code != "INITIAL_STAGE"' in renderer
    assert 'command_code="RESEARCH.REQUEST_REFRESH"' in renderer
    assert 'openTitle.textContent = isCommand' in driver
    assert '"Пересобрать связь стадий"' in driver
    assert 'this.setRowStatus(row, "Выполняется", 50, "RUNNING")' in driver
    assert 'this.setRowStatus(row, "В очереди", 10, "WARNING")' in driver
    assert '"profit_funnel_lineage"' in cycle
    assert '"src/scripts/build_profit_funnel_transition_lineage_v2.py"' in cycle
    assert "status IN ('PENDING','RUNNING')" in resolver
    assert "status = active_refresh_status" in resolver
