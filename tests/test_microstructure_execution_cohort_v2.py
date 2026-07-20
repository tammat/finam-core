from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_migration_preserves_history_and_schedules_autonomous_cohort() -> None:
    sql = (ROOT / "sql/analytics/154_microstructure_execution_cohort_v2.sql").read_text()
    assert "HISTORICAL_BAR_ONLY" in sql
    assert "MICROSTRUCTURE_ONLY" in sql
    assert "MICROSTRUCTURE_VERIFIED" in sql
    assert "SESSION_EXECUTION_EDGE_MICROSTRUCTURE_V2" in sql
    assert "SESSION_EXECUTION_EDGE_V2" in sql


def test_v3_schedule_runs_intraday_and_registers_split_panel_i18n() -> None:
    sql = (ROOT / "sql/analytics/160_microstructure_autonomous_cohort_v3.sql").read_text()
    assert "window_start=time '06:50'" in sql
    assert "interval_minutes=30" in sql
    assert "execution_microstructure.title" in sql
    assert "execution_historical.title" in sql
    assert "GRANT SELECT ON analytics.oos_remediation_candidate_v1 TO finam" in sql


def test_scheduler_uses_resource_limited_v2_executor() -> None:
    source = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert '"SESSION_EXECUTION_EDGE_V2": "src/scripts/build_session_execution_edge_v1.py"' in source
    assert '"SESSION_EDGE_MAX_MARKETS": "8"' in source
    assert '"MICROSTRUCTURE_MIN_COVERAGE": "0.80"' in source


def test_builder_waits_for_fresh_depth_before_heavy_rebuild() -> None:
    source = (ROOT / "src/scripts/build_session_execution_edge_v1.py").read_text()
    assert "fresh_microstructure_symbols(cur)" in source
    assert "WAITING_FOR_FRESH_MICROSTRUCTURE" in source
    assert "MICROSTRUCTURE_MIN_FRESH_SYMBOLS" in source
    assert 'configuration["regime_policy"].get("allowed_regimes")' in source
    assert "ALLOWED_REGIMES[family]" not in source
    assert "status_code='WAITING_FUTURE_DATA'" in source
    assert "active_oos_symbols" in source


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


def test_control_center_splits_historical_and_microstructure_cohorts() -> None:
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py").read_text()
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py").read_text()
    assert "DISTINCT ON (cohort_code)" in resolver
    assert '"execution_microstructure"' in renderer
    assert '"execution_historical"' in renderer
    assert '"cohort_code"' in renderer


def test_block_rows_offer_audited_review_instead_of_risk_bypass() -> None:
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py").read_text()
    driver = (ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert 'section_code == "block"' in renderer
    assert 'command_code="RESEARCH.RUN_EDGE_SEARCH"' in renderer
    assert "openBlockActions" in driver
    assert "Прямой обход риск-контроля запрещён" in driver
    assert "Проверить и снять блок" in driver
