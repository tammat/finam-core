from pathlib import Path


def test_research_page_reads_live_flow_and_discovery_checkpoint() -> None:
    resolver = Path(
        "src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py"
    ).read_text(encoding="utf-8")
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py"
    ).read_text(encoding="utf-8")
    assert "runtime_guard_signal_registry_v1" in resolver
    assert "public.fills" in resolver
    assert "public.closed_trades" in resolver
    assert "edge_regime_discovery_run_v3" in resolver
    for tile in ("live_signals", "paper_fills", "closed_trades", "regime_progress"):
        assert f'_tile("{tile}"' in renderer


def test_research_live_flow_labels_are_i18n_resources() -> None:
    migration = Path("sql/presentation/132_research_live_flow_i18n_v1.sql").read_text(
        encoding="utf-8"
    )
    assert "research.tile.live_signals" in migration
    assert "research.tile.paper_fills" in migration
    assert "research.tile.closed_trades" in migration
    assert "research.tile.regime_progress" in migration
    assert "research.current.regime_tasks.value" in migration
