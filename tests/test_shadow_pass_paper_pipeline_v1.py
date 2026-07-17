from pathlib import Path


def test_shadow_pass_contract_is_strict_and_database_driven() -> None:
    migration=Path("sql/analytics/081_shadow_pass_paper_pipeline_v1.sql").read_text()
    evaluator=Path("src/scripts/evaluate_shadow_pass_v1.py").read_text()
    for field in ("minimum_closed","minimum_calendar_days","minimum_profit_factor",
                  "minimum_expectancy","maximum_drawdown","minimum_cost_coverage",
                  "minimum_tested_regimes","minimum_positive_regime_share"):
        assert field in migration and field in evaluator
    assert 'return ("FAIL",reasons) if reasons else ("PASS"' in evaluator


def test_only_shadow_pass_creates_non_runtime_paper_candidate() -> None:
    source=Path("src/scripts/evaluate_shadow_pass_v1.py").read_text()
    assert 'if decision=="PASS"' in source
    assert "READY_FOR_PAPER_OBSERVATION" in source
    assert "TRUE,FALSE,FALSE,FALSE" in source
    assert 'print("runtime_allowed=0")' in source


def test_monitor_alerts_on_failure_staleness_and_unsafe_rows() -> None:
    source=Path("src/scripts/monitor_shadow_pipeline_v1.py").read_text()
    assert "age>600" in source
    assert "SHADOW_OBSERVER_FAILED" in source
    assert "SHADOW_UNSAFE_ROWS" in source
    assert "status_code='RESOLVED'" in source


def test_control_panel_has_process_alerts_and_forward_blockers() -> None:
    resolver=Path("src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py").read_text()
    renderer=Path("src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py").read_text()
    catalog=Path("sql/presentation/076_shadow_pipeline_control_i18n_v1.sql").read_text()
    assert "def _shadow_process" in resolver
    assert "def _shadow_alerts" in resolver
    assert "def _forward_blockers" in resolver
    assert '("shadow_process", tuple(view_model.shadow_process))' in renderer
    assert "research.control.section.shadow_process.title" in catalog
    assert "status.no_forward_pass" in catalog
