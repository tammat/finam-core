from pathlib import Path


def test_lifecycle_i18n_is_short_and_complete() -> None:
    migration = Path("sql/presentation/148_operator_action_lifecycle_i18n_v1.sql").read_text()
    for key in (
        "home.operator.status.measuring",
        "home.operator.status.measure_due",
        "home.operator.status.improved",
        "home.operator.status.no_effect",
        "home.operator.status.degraded",
        "home.operator.next.measure",
        "home.operator.next.view",
    ):
        assert key in migration


def test_progress_bar_understands_all_terminal_results() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    for label in ("Измерение", "Измерить", "Улучшение", "Без эффекта", "Ухудшение", "Устарело"):
        assert f'"{label}"' in source


def test_inactive_decisions_are_marked_stale() -> None:
    source = Path("src/scripts/build_operator_decision_workspace_v2.py").read_text()
    assert "active_transitions" in source
    assert "freshness_code='STALE'" in source


def test_terminal_and_blocked_dialogs_keep_useful_actions() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert '"Обновить решение"' in source
    assert '"Открыть допуски"' in source
    assert '"Обновить данные"' in source


def test_operator_cards_open_scoped_action_dialogs() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert "openOperatorCardActions(card, emit)" in source
    assert 'node.node_id.startsWith("home.operator.")' in source
    assert 'openTitle.textContent = "Открыть раздел"' in source


def test_refresh_command_is_db_driven() -> None:
    migration = Path("sql/marketcore_action/149_operator_decision_refresh_v2.sql").read_text()
    handler = Path("src/marketcore/action/handler_registry_v2.py").read_text()
    worker = Path("src/marketcore/action/command_worker_v2.py").read_text()
    assert "OPERATOR_DECISION_REFRESH" in migration
    assert "OPERATOR.REFRESH_DECISION" in migration
    assert '"operator.decision.refresh"' in handler
    assert "_refresh_operator_decision" in worker
