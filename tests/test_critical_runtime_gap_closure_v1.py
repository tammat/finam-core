from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_portfolio_risk_uses_only_real_v5_paper_positions():
    source = (ROOT / "src/scripts/build_portfolio_risk_state.py").read_text()
    assert "paper_research_position_projection_v1" in source
    assert "portfolio_scope LIKE 'FRESH_V5%'" in source
    assert "symbol NOT LIKE 'TEST@%'" in source
    assert "FROM runtime_capital_allocator" not in source
    assert '"COMMODITIES", "EQUITIES", "FX", "METALS"' in source


def test_inactive_expired_contract_is_not_a_scheduler_failure():
    source = (ROOT / "src/scripts/sync_market_contract_specs_v1.py").read_text()
    assert "EXPIRED_OR_INACTIVE_CONTRACT" in source
    assert "runtime_active_universe" in source


def test_data_quality_rejection_does_not_activate_global_kill_switch():
    source = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    block = source[source.index("PIPE_PORTFOLIO_RISK_BLOCK"):source.index("PIPE_PORTFOLIO_RISK_REDUCE")]
    assert "_kill_switch_active = True" not in block
    assert "persistent_kill_switch.activate" in source


def test_required_runtime_grants_are_migrated():
    sql = (ROOT / "sql/analytics/240_critical_runtime_gap_closure_v1.sql").read_text()
    assert "runtime_strategy_assignment_v1 TO alex" in sql
    assert "regime_strategy_routing_policy_v1 TO alex" in sql
    assert "paper_closed_trade_materializer_checkpoint_v2 TO alex" in sql


def test_runtime_risk_builder_does_not_run_owner_only_ddl():
    source = (ROOT / "src/scripts/build_portfolio_risk_state.py").read_text()
    assert "CREATE TABLE IF NOT EXISTS portfolio_risk_state" not in source


def test_persistent_kill_switch_runtime_path_does_not_run_ddl():
    source = (ROOT / "src/finam_core/risk/persistent_kill_switch.py").read_text()
    for method_name, next_method in (
        ("def activate(", "def deactivate("),
        ("def deactivate(", "def get_state("),
        ("def get_state(", "def is_active("),
    ):
        block = source[source.index(method_name):source.index(next_method)]
        assert "ensure_schema()" not in block


def test_home_trade_tables_include_colored_daily_total():
    source = (
        ROOT
        / "src/marketcore/presentation/workspace_v2/renderer/home_compact_v1_domain_renderer.py"
    ).read_text()
    assert '"Итого за сегодня"' in source
    assert 'total_status = "PROFIT"' in source
    assert '"LOSS" if daily_total' in source


def test_lifecycle_is_single_position_per_scope_and_symbol():
    repository = (
        ROOT / "src/finam_core/execution/position_lifecycle_state_repository.py"
    ).read_text()
    pipeline = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    migration = (
        ROOT / "sql/analytics/241_v5_lifecycle_and_timeframe_integrity_v1.sql"
    ).read_text()
    assert "ON CONFLICT (portfolio_scope, symbol)" in repository
    assert "paper_pipeline_lifecycle_projection_reconcile_v2" in pipeline
    assert "UNIQUE (portfolio_scope,symbol)" in migration
    avg_price_block = pipeline[
        pipeline.index("def _position_avg_price_for_symbol"):
        pipeline.index("def _exit_fallback_atr")
    ]
    assert avg_price_block.index("positions =") < avg_price_block.index("broker_avg =")
    assert 'EXECUTION_MODE", "paper"' in avg_price_block


def test_materializer_never_restores_live_timeframe():
    source = (
        ROOT / "src/scripts/analytics/materialize_closed_trades_from_fills_v1.py"
    ).read_text()
    assert "def analytical_timeframe" in source
    assert 'timeframe != "LIVE"' in source
    assert '"timeframe": analytical_timeframe' in source


def test_fast_ingestion_timeout_is_failure_only_when_data_is_stale():
    source = (
        ROOT / "src/scripts/ingestion/run_continuous_market_bars_ingestion.py"
    ).read_text()
    assert "def target_is_fresh" in source
    assert "already_fresh={fresh}" in source
    assert "return fresh" in source


def test_cpu_heavy_edge_research_is_outside_market_hours():
    sql = (
        ROOT / "sql/analytics/242_research_scheduler_market_hours_isolation_v1.sql"
    ).read_text()
    assert "SESSION_EXECUTION_EDGE_MICROSTRUCTURE_V2" in sql
    assert "window_start=time '00:10:00'" in sql
    assert "window_end=time '06:00:00'" in sql


def test_ui_active_trades_are_projection_backed_not_ghost_signals():
    source = (
        ROOT
        / "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py"
    ).read_text()
    active_branch = source[source.index("'ACTIVE'::text"):source.index("), ranked AS")]
    assert "paper_research_position_projection_v1" in active_branch
    assert "abs(position.net_qty)>" in active_branch
    assert "s.status='FILLED'" not in active_branch
    assert "x.event_status='ACTIVE'" in source


def test_brent_online_uses_bounded_http_retries():
    source = (ROOT / "src/scripts/run_moex_brent_online_v1.py").read_text()
    assert "Retry(" in source
    assert "connect=3" in source
    assert "timeout=(5,20)" in source


def test_legacy_filled_signals_are_quarantined_outside_v5():
    sql = (
        ROOT / "sql/analytics/243_legacy_filled_signal_quarantine_v1.sql"
    ).read_text()
    assert "LEGACY_FILLED_WITHOUT_CANONICAL_TRADE_OR_V5_SCOPE" in sql
    assert "sf.portfolio_scope LIKE 'FRESH_V5%'" in sql
    assert "status='ARCHIVED_LEGACY'" in sql
