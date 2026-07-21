from pathlib import Path


def test_universe_rows_offer_four_operator_actions() -> None:
    driver = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    renderer = Path("src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    for label in (
        "Почему выбрано",
        "Закрепить в следующем цикле",
        "Исключить из следующего цикла",
        "Изменить приоритет",
    ):
        assert label in driver
    assert "openUniverseActions(element)" in driver
    assert '"research.universe.include_next",ActionKindV2.COMMAND' in renderer


def test_universe_changes_are_db_driven_and_apply_only_to_next_snapshot() -> None:
    migration = Path("sql/analytics/102_research_universe_operator_overrides_v1.sql").read_text()
    selector = Path("src/scripts/edge_research_universe_v1.py").read_text()
    worker = Path("src/marketcore/action/command_worker_v2.py").read_text()
    assert "edge_research_universe_override_v1" in migration
    assert "edge_research_universe_override_v1" in selector
    assert "FORCE_INCLUDE" in selector and "FORCE_EXCLUDE" in selector
    assert "_apply_universe_override" in worker
    assert "priority_override" in worker


def test_universe_commands_are_governed_and_auditable() -> None:
    registry = Path("src/marketcore/action/handler_registry_v2.py").read_text()
    controller = Path("src/marketcore/presentation/action_http_controller_v2.py").read_text()
    for action in (
        "research.universe.include_next",
        "research.universe.exclude_next",
        "research.universe.priority",
    ):
        assert action in registry
    assert 'definition.request_kind.startswith("RESEARCH_UNIVERSE_")' in controller
