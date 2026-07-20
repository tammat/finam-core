from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_priority_migration_is_weighted_audited_and_scheduled() -> None:
    source = (ROOT / "sql/analytics/161_dynamic_microstructure_priority_v1.sql").read_text()
    assert "microstructure_priority_policy_v1" in source
    assert "microstructure_priority_decision_v1" in source
    assert "microstructure_research_priority_v1" in source
    assert "selected_for_detail" in source
    assert "selected_for_analysis" in source
    assert "MICROSTRUCTURE_PRIORITY_REFRESH_V1" in source
    assert "OOS_DATA_DEFICIT" in source
    assert "MICROSTRUCTURE_COVERAGE_GAP" in source


def test_priority_refresh_is_an_executable_db_snapshot() -> None:
    source = (ROOT / "src/scripts/refresh_microstructure_priority_v1.py").read_text()
    assert "INSERT INTO analytics.microstructure_priority_decision_v1" in source
    assert "FROM analytics.microstructure_research_priority_v1" in source
    assert 'if __name__ == "__main__"' in source


def test_scheduler_and_consumers_use_the_dynamic_ranking() -> None:
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    collector = (ROOT / "src/scripts/run_finam_microstructure_ws_v1.py").read_text()
    builder = (ROOT / "src/scripts/build_session_execution_edge_v1.py").read_text()
    assert '"MICROSTRUCTURE_PRIORITY_REFRESH_V1"' in scheduler
    assert '"SESSION_EDGE_MAX_MARKETS": "4"' in scheduler
    assert "selected_for_detail" in collector
    assert "PRIORITY_REFRESH_SECONDS" in collector
    assert "selected_for_analysis" in builder


def test_control_center_exposes_priority_reasons() -> None:
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py").read_text()
    viewmodel = (ROOT / "src/marketcore/presentation/workspace_v2/viewmodel/control_center_v2_viewmodel.py").read_text()
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py").read_text()
    assert "_microstructure_priorities" in resolver
    assert "reason_code" in resolver
    assert "microstructure_priorities" in viewmodel
    assert '("microstructure_priorities"' in renderer
