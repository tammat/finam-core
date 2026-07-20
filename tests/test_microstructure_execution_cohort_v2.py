from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_migration_preserves_history_and_schedules_autonomous_cohort() -> None:
    sql = (ROOT / "sql/analytics/154_microstructure_execution_cohort_v2.sql").read_text()
    assert "HISTORICAL_BAR_ONLY" in sql
    assert "MICROSTRUCTURE_ONLY" in sql
    assert "MICROSTRUCTURE_VERIFIED" in sql
    assert "SESSION_EXECUTION_EDGE_MICROSTRUCTURE_V2" in sql
    assert "SESSION_EXECUTION_EDGE_V2" in sql


def test_scheduler_uses_resource_limited_v2_executor() -> None:
    source = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert '"SESSION_EXECUTION_EDGE_V2": "src/scripts/build_session_execution_edge_v1.py"' in source
    assert '"SESSION_EDGE_MAX_MARKETS": "8"' in source
    assert '"MICROSTRUCTURE_MIN_COVERAGE": "0.80"' in source


def test_builder_requires_real_quote_coverage_and_fixed_cursor() -> None:
    source = (ROOT / "src/scripts/build_session_execution_edge_v1.py").read_text()
    assert "load_search_configuration(cur)" in source
    assert "load_search_configuration(cursor)" not in source
    assert "MICROSTRUCTURE_ONLY" in source
    assert "microstructure_coverage" in source
    assert "MICROSTRUCTURE_DATA_UNVERIFIED" in source


def test_control_center_exposes_quote_evidence_and_readable_block_summary() -> None:
    source = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py").read_text()
    for field in ("best_bid", "best_ask", "bid_depth", "ask_depth", "exchange_ts"):
        assert field in source
    assert "blocking_rule" in source
    assert "lost_signals" in source
    assert "loss_share_pct" in source
    assert "evidence_json->>'sample_symbols'" in source


def test_block_rows_offer_audited_review_instead_of_risk_bypass() -> None:
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py").read_text()
    driver = (ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert 'section_code == "block"' in renderer
    assert 'command_code="RESEARCH.RUN_EDGE_SEARCH"' in renderer
    assert "openBlockActions" in driver
    assert "Прямой обход риск-контроля запрещён" in driver
    assert "Проверить и снять блок" in driver
