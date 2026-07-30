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
