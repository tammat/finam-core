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
    assert '"NO_DATA" if not gate_total' in resolver
    assert '"WARNING" if item.status == "NO_DATA"' in renderer
