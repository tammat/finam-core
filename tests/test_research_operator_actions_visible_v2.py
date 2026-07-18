from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def test_research_tables_expose_operator_action_column():
    source=(ROOT/"src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    assert source.count('"operator_action"') >= 2
    assert source.count('key="research.operator_actions.open"') == 2


def test_operator_action_labels_are_i18n_resources():
    migration=(ROOT/"sql/analytics/116_research_operator_actions_i18n_v1.sql").read_text()
    assert "research.universe.column.operator_action" in migration
    assert "research.scout.column.operator_action" in migration
    assert "research.operator_actions.open.tooltip" in migration
