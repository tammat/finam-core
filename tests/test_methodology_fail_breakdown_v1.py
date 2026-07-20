from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def test_resolver_uses_only_latest_methodology_cohort() -> None:
    source=(ROOT/"src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    assert "SELECT scenario_run_id" in source
    assert "ORDER BY created_at DESC LIMIT 1" in source
    for gate in ("statistical_pass","robustness_pass","holdout_pass","execution_pass","capacity_pass","portfolio_pass"):
        assert gate in source


def test_renderer_exposes_six_gate_failure_rows() -> None:
    domain=(ROOT/"src/marketcore/presentation/workspace_v2/domain/research_snapshot_v2.py").read_text()
    renderer=(ROOT/"src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    migration=(ROOT/"sql/analytics/094_methodology_fail_breakdown_i18n_v1.sql").read_text()
    assert "MethodologyGateFailureV1" in domain
    assert "_methodology_failure_table" in renderer
    assert "research.failures.title" in renderer
    for gate in ("statistical","robustness","holdout","execution","capacity","portfolio"):
        assert f"research.failures.gate.{gate}" in migration


def test_no_data_is_not_rendered_as_success() -> None:
    resolver=(ROOT/"src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    renderer=(ROOT/"src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    assert '"NOT_EVALUATED" if not evaluated' in resolver
    assert '("NO_DATA","NOT_EVALUATED")' in renderer


def test_methodology_is_a_sequential_funnel_not_six_parallel_failures() -> None:
    evaluator=(ROOT/"src/scripts/evaluate_edge_methodology_contract_v1.py").read_text()
    resolver=(ROOT/"src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    domain=(ROOT/"src/marketcore/presentation/workspace_v2/domain/research_snapshot_v2.py").read_text()
    assert 'gate_statuses[gate_code] = "NOT_EVALUATED"' in evaluator
    assert '"gate_statuses":gate_statuses' in evaluator
    assert "first_gate_failure" in evaluator
    assert 'counts["NOT_EVALUATED"]' in resolver
    assert "not_evaluated: int" in domain
    assert '"base",gate_total,gate_total-base_passed' in resolver
    assert "NEGATIVE_COST_ADJUSTED_EXPECTANCY" in resolver
    assert "INSUFFICIENT_TRADES" in resolver


def test_methodology_rows_offer_audited_double_click_actions() -> None:
    renderer=(ROOT/"src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    driver=(ROOT/"src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    migration=(ROOT/"sql/analytics/157_methodology_funnel_i18n_v1.sql").read_text()
    assert 'command_code="RESEARCH.RUN_EDGE_SEARCH"' in renderer
    assert "openMethodologyActions" in driver
    assert 'nodeId.startsWith("research.failures.")' in driver
    assert "Повторить адресно" in driver
    assert "research.domain.not_passed" in migration
