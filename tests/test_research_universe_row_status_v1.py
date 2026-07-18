from pathlib import Path


def test_universe_row_reads_latest_process_status() -> None:
    resolver = Path("src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    assert "q.request_kind LIKE 'RESEARCH_UNIVERSE_%%'" in resolver
    assert "split_part(coalesce(q.target_id,''),'|',1)=u.symbol" in resolver
    assert "a.process_id" in resolver
    assert "action_progress" in resolver


def test_universe_table_renders_status_progress_in_same_row() -> None:
    renderer = Path("src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    domain = Path("src/marketcore/presentation/workspace_v2/domain/research_snapshot_v2.py").read_text()
    assert 'columns=("selected","symbol","category","bars","rank","reason","status")' in renderer
    assert '_process_status(f"research.universe.{index}.status",item)' in renderer
    assert "process_id: str | None" in domain
    assert "progress_pct: float" in domain
