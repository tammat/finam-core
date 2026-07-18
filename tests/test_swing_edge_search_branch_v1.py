from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parents[1]


def test_swing_branch_is_db_driven_and_fail_aware() -> None:
    migration = (ROOT / "sql/analytics/106_swing_edge_search_branch_v1.sql").read_text()
    runner = (ROOT / "src/scripts/run_swing_edge_search_cycle_v1.py").read_text()
    factory = (ROOT / "src/scripts/build_swing_hypothesis_factory_v1.py").read_text()
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert "SWING_EDGE_SEARCH_CYCLE_V1" in scheduler
    assert "manual_algorithm_start\":false" in migration
    assert "edge_next_research_plan_v1" in runner
    assert "source_failure_reasons" in factory
    assert "NEGATIVE_COST_ADJUSTED_EXPECTANCY" in factory
    assert '"H1"' in migration and '"H4"' in migration and '"D1"' in migration
    assert '"pass_gates":"unchanged"' in migration
    assert '"REAL_TRADING_ENABLED": "0"' in runner


def test_swing_failures_create_future_only_db_plan() -> None:
    validator = (ROOT / "src/scripts/run_swing_selection_validation_engine_v1.py").read_text()
    generator = (ROOT / "src/scripts/generate_next_swing_research_plan_v1.py").read_text()
    migration = (ROOT / "sql/analytics/107_swing_fail_driven_next_plan_v1.sql").read_text()
    assert "VALIDATION_FOLDS_UNSTABLE" in validator
    assert "MULTIPLE_TESTING_SIGNIFICANCE_FAILED" in validator
    assert "swing_next_research_plan_v1" in generator
    assert "FUTURE_DATA_ONLY" in generator
    assert "pass_gates=UNCHANGED" in generator
    assert "SWING_NEXT_RESEARCH_PLAN_V1" in (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert "CHECK(pass_gates_unchanged)" in migration


def test_swing_future_executor_has_full_methodology_and_recovery() -> None:
    executor=(ROOT/"src/scripts/run_swing_future_execution_v1.py").read_text()
    monitor=(ROOT/"src/scripts/monitor_swing_process_v1.py").read_text()
    migration=(ROOT/"sql/analytics/108_swing_future_execution_lifecycle_v1.sql").read_text()
    for gate in ("statistical","robustness","holdout","execution","capacity","portfolio"):
        assert f'"{gate}"' in executor
    for risk in ("margin_ready","spec_ready","overnight_gap_stress","roll_required"):
        assert risk in executor
    assert "holdout_fingerprint" in migration
    assert "heartbeat_at" in migration and "STALE_HEARTBEAT_RECOVERED" in monitor
    assert "SWING_FUTURE_EXECUTION_V1" in (ROOT/"src/scripts/run_db_job_scheduler_v1.py").read_text()


def test_swing_branch_schema_is_installed_in_postgres() -> None:
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('analytics.swing_edge_search_run_v1'), to_regclass('analytics.swing_edge_search_step_run_v1')")
            assert cursor.fetchone() == ("analytics.swing_edge_search_run_v1", "analytics.swing_edge_search_step_run_v1")
            cursor.execute("SELECT enabled,executor_code FROM analytics.system_job_schedule_v1 WHERE job_code='SWING_EDGE_SEARCH_WEEKEND'")
            assert cursor.fetchone() == (True, "SWING_EDGE_SEARCH_CYCLE_V1")


def test_swing_final_gate_uses_real_execution_and_portfolio_evidence() -> None:
    script = (ROOT / "src/scripts/run_swing_future_execution_v1.py").read_text()
    assert "load_swing_execution_contract" in script
    assert "portfolio_daily_pnl" in script
    assert "portfolio_overlap_days" in script
    assert "median_gap_bps" in script
    assert '"margin_ready"' in script and '"roll_ready"' in script
    assert '"carry_ready"' in script and "execution_symbol" in script


def test_swing_lifecycle_is_db_driven_and_live_remains_blocked() -> None:
    migration = (ROOT / "sql/analytics/109_swing_autonomous_lifecycle_v1.sql").read_text()
    script = (ROOT / "src/scripts/run_swing_autonomous_lifecycle_v1.py").read_text()
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert "swing_candidate_lifecycle_v1" in migration
    assert "SWING_AUTONOMOUS_LIFECYCLE_V1" in scheduler
    assert "verdict_code='PASS' AND r.promotion_allowed" in script
    assert "FORWARD" in script and "SHADOW" in script and "PAPER" in script
    assert "live_allowed=0" in script
    observer = (ROOT / "src/scripts/run_swing_forward_shadow_router_v1.py").read_text()
    assert "JOIN analytics.swing_candidate_lifecycle_v1" in observer


def test_swing_panel_has_auditable_double_click_details() -> None:
    page = (ROOT / "src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py").read_text()
    assert "swing_candidate_lifecycle_v1" in page
    assert "ondblclick" in page
    assert "Статистика" in page and "Устойчивость" in page
    assert "Исполнение" in page and "Портфель" in page


def test_swing_bars_are_refreshed_incrementally_by_db_scheduler() -> None:
    aggregator = (ROOT / "src/scripts/build_canonical_swing_timeframes_v1.py").read_text()
    migration = (ROOT / "sql/analytics/110_swing_market_bar_refresh_schedule_v1.sql").read_text()
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    page = (ROOT / "src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py").read_text()
    assert "DELETE FROM analytics.swing_market_bars_v1" not in aggregator
    assert "ON CONFLICT(symbol,timeframe,ts) DO UPDATE" in aggregator
    assert "SWING_BARS_REFRESH_V1" in migration and "SWING_BARS_REFRESH_V1" in scheduler
    assert "future_bars" in page and "Будущие данные" in page


def test_swing_monitor_persists_freshness_and_eta() -> None:
    migration = (ROOT / "sql/analytics/111_swing_future_data_readiness_v1.sql").read_text()
    monitor = (ROOT / "src/scripts/monitor_swing_process_v1.py").read_text()
    page = (ROOT / "src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py").read_text()
    assert "swing_future_data_readiness_v1" in migration
    assert "FUTURE_DATA_SOURCE_STALE" in monitor
    assert "estimated_ready_at" in monitor and "remaining_bars" in monitor
    assert "monitor_run_id" in migration and "estimate_ready" in monitor
    assert "Прогноз готовности" in page and "Нет источника" in page


def test_swing_uses_one_execution_contract_across_all_stages() -> None:
    contract = (ROOT / "src/scripts/swing_execution_contract_v1.py").read_text()
    future = (ROOT / "src/scripts/run_swing_future_execution_v1.py").read_text()
    lifecycle = (ROOT / "src/scripts/run_swing_autonomous_lifecycle_v1.py").read_text()
    shadow = (ROOT / "src/scripts/run_swing_forward_shadow_router_v1.py").read_text()
    assert "broker_fee_profile_v1" in contract and "exchange_fee_profile_v1" in contract
    assert "slippage_profile_v1" in contract and "account_tax_profile_v1" in contract
    assert "market_contract_cost_spec_v1" in contract
    for source in (future, lifecycle, shadow):
        assert "swing_execution_contract_v1" in source
    assert "trailing_profit_factor" in lifecycle and "max_drawdown_rub" in lifecycle


def test_swing_paper_engine_is_risk_guarded_and_never_live() -> None:
    migration = (ROOT / "sql/analytics/112_swing_canonical_paper_engine_v1.sql").read_text()
    engine = (ROOT / "src/scripts/run_swing_paper_engine_v1.py").read_text()
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    page = (ROOT / "src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py").read_text()
    for table in ("swing_paper_order_v1", "swing_paper_fill_v1", "swing_paper_position_v1", "swing_paper_trade_v1", "swing_paper_risk_decision_v1"):
        assert table in migration
    for guard in ("KILL_SWITCH_ACTIVE", "MAX_OPEN_POSITIONS", "MARGIN_LIMIT", "DAILY_LOSS_LIMIT", "DRAWDOWN_LIMIT"):
        assert guard in engine
    assert "broker_order_sent boolean NOT NULL DEFAULT false CHECK(NOT broker_order_sent)" in migration
    assert "live_allowed boolean NOT NULL DEFAULT false CHECK(NOT live_allowed)" in migration
    assert "SWING_PAPER_ENGINE_V1" in scheduler
    assert "Paper PnL" in page and "После налога" in page
    sync = (ROOT / "src/scripts/sync_market_contract_specs_v1.py").read_text()
    assert "INITIALMARGIN" in sync and "BUYSELLFEE" in sync and "SCALPERFEE" in sync


def test_swing_paper_contract_is_installed_and_official_costs_are_ready() -> None:
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT count(*) FROM analytics.market_contract_cost_spec_v1
              WHERE symbol IN ('BRQ6@RTSX','NGN6@RTSX') AND initial_margin>0 AND buy_sell_fee>0
                AND source_version='MOEX_ISS_CONTRACT_SPEC_V1'""")
            assert cursor.fetchone()[0] == 2
            cursor.execute("SELECT count(*) FROM analytics.swing_paper_order_v1 WHERE broker_order_sent OR live_allowed")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT count(*) FROM analytics.swing_paper_strategy_v1 WHERE live_allowed")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT enabled,executor_code FROM analytics.system_job_schedule_v1 WHERE job_code='SWING_PAPER_ENGINE'")
            assert cursor.fetchone() == (True, "SWING_PAPER_ENGINE_V1")


def test_active_control_center_v2_exposes_swing_lifecycle() -> None:
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py").read_text()
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py").read_text()
    migration = (ROOT / "sql/analytics/112_swing_canonical_paper_engine_v1.sql").read_text()
    assert "swing_summary" in resolver and "swing_paper_trade_v1" in resolver
    assert '"swing_lifecycle"' in renderer and "_swing_rows" in renderer
    assert "research.control.section.swing_lifecycle.title" in migration


def test_swing_monitor_adapts_uuids_and_failures_are_rolled_up() -> None:
    monitor = (ROOT / "src/scripts/monitor_swing_process_v1.py").read_text()
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    migration = (ROOT / "sql/analytics/113_system_job_failure_rollup_v1.sql").read_text()
    driver = (ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    domain = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py").read_text()
    assert "str(monitor_run_id),str(item[\"plan_item_id\"])" in monitor
    assert "system_job_failure_rollup_v1" in scheduler and "occurrences+1" in scheduler
    assert "DELETE FROM analytics.system_job_run_v1" in migration
    assert "openSwingDetails" in driver and "isSwingRow" in driver
    assert '"progress_pct"' in domain and "Межрыночное опережение" in domain
