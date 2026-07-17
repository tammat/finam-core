from pathlib import Path


def test_research_dashboard_reads_persisted_system_runs_and_analysis() -> None:
    resolver=Path("src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    assert "research_process_v1" in resolver
    assert "edge_search_step_run_v1" in resolver
    assert "research_recommendation_action_v1" in resolver
    assert "recommendation_code" in resolver
    assert "LIMIT 10" in resolver


def test_research_dashboard_renders_compact_audit_table() -> None:
    renderer=Path("src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    assert "research.audit.table" in renderer
    assert 'columns=("status","started","steps","duration","outcome","reason","analysis","recommendation")' in renderer
    assert 'value=item.explanation' in renderer
    assert '"research.edge_search.run",ActionKindV2.COMMAND' in renderer


def test_audit_dashboard_is_read_only() -> None:
    resolver=Path("src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    assert "subprocess" not in resolver
    assert "INSERT INTO analytics.edge_search" not in resolver
    assert "UPDATE analytics.edge_search" not in resolver
