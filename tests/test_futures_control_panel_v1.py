from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def test_futures_panel_is_db_backed_and_russian():
    domain=(ROOT/"src/marketcore/presentation/workspace_v2/domain/research_snapshot_v2.py").read_text()
    resolver=(ROOT/"src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    renderer=(ROOT/"src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    migration=(ROOT/"sql/analytics/098_futures_control_panel_v1.sql").read_text()
    assert "FuturesRollItemV1" in domain
    assert "futures_roll_decision_v1" in resolver
    assert "_futures_roll_table(s.futures_roll_items)" in renderer
    assert "research.futures.status.ready" in migration
    assert "Фьючерсы" in migration and "Ликвидность" in migration and "Плечо" in migration


def test_roll_status_contains_progress_and_audit_reason():
    renderer=(ROOT/"src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    assert '"progress_pct":item.progress_pct' in renderer
    assert "item.decision_code.lower()" in renderer
