from pathlib import Path


def test_paper_ready_is_not_derived_from_tautology() -> None:
    source=Path("src/scripts/build_paper_runtime_real_data_v1.py").read_text()
    assert 'closed_total >= 0' not in source
    assert 'paper_status = "WAITING_ADMISSION"' in source
    assert 'paper_status = "WAITING_SIGNALS"' in source
    assert 'paper_status = "OBSERVING"' in source


def test_shadow_freshness_is_visible_and_localized() -> None:
    resolver=Path("src/marketcore/presentation/workspace_v2/resolver/intraday_v2_resolver.py").read_text()
    renderer=Path("src/marketcore/presentation/workspace_v2/renderer/intraday_v2_domain_renderer.py").read_text()
    catalog=Path("sql/presentation/075_intraday_runtime_status_i18n_v1.sql").read_text()
    assert 'total_seconds()>900' in resolver
    assert '"STALE"' in resolver and '"WAITING_CANDIDATE"' in resolver
    assert '"shadow_status",s.shadow_status,"DOMAIN_CODE"' in renderer
    for key in ('status.waiting_admission','status.waiting_signals','status.observing','status.waiting_candidate','status.stale'):
        assert key in catalog
