from pathlib import Path


def test_research_summary_is_compact_traffic_light_tiles() -> None:
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py"
    ).read_text()
    css = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css"
    ).read_text()
    assert 'RenderNodeTypeV2.GRID,"research.tiles"' in renderer
    assert 'f"research.tile.{code}"' in renderer
    assert '[data-mc-node-id^="research.tile."]::before' in css
    assert 'RenderNodeTypeV2.METRIC_LIST,"research.metrics"' not in renderer


def test_recommendation_cell_opens_real_db_backed_process_choices() -> None:
    driver = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js"
    ).read_text()
    assert 'endsWith(".recommendation")' in driver
    assert 'openResearchActions(element)' in driver
    assert "option.action_id" in driver
    assert "option.command_code" in driver
    assert "dataset.mcActions" in driver


def test_research_page_auto_refreshes_process_state() -> None:
    shell = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js"
    ).read_text()
    assert 'currentTargetId === "container.research"' in shell
    assert "globalObject.setInterval" in shell
    assert "10000" in shell


def test_status_is_first_column_and_uses_progress_bar() -> None:
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py"
    ).read_text()
    driver = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js"
    ).read_text()
    assert 'columns=("status","started","steps","duration","outcome","reason","analysis","recommendation")' in renderer
    assert '"Выполнено": 100' in driver
    assert '"Выполняется": 50' in driver
    assert '"Ожидает": 10' in driver


def test_audit_headers_are_informative_and_can_wrap() -> None:
    migration = Path("sql/presentation/074_edge_search_audit_i18n_v1.sql").read_text()
    css = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    for label in ("Состояние процесса", "Время запуска", "Этапы выполнения", "Итог поиска", "Следующее действие", "Анализ результата"):
        assert label in migration
    assert '[data-mc-node="table_header_cell"] { white-space: normal;' in css
