from pathlib import Path


def test_research_initial_payload_is_bounded_and_summary_is_actionable() -> None:
    resolver = Path(
        "src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py"
    ).read_text()
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py"
    ).read_text()

    assert "LIMIT 80" in resolver
    assert "analytics.microstructure_health_v1" in resolver
    assert "analytics.execution_model_health_v1" not in resolver
    assert 'def _current_cycle_card(s):' in renderer
    assert '"research.current.stage"' in renderer
    assert '"research.current.reason"' in renderer
    assert '"research.current.next"' in renderer
    assert "if s.validation_funnel_available:" in renderer
    assert "if s.strategy_degradation:" in renderer


def test_current_cycle_labels_are_russian_and_short() -> None:
    migration = Path(
        "sql/presentation/129_research_current_cycle_i18n_v1.sql"
    ).read_text()
    for label in ("Текущий поиск", "Статус", "Этап", "Прогресс, %", "Причина", "Далее"):
        assert label in migration
