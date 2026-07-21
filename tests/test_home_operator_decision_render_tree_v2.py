from pathlib import Path

from marketcore.presentation.render_tree.v2 import RenderNodeTypeV2
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def test_home_exposes_ranked_non_green_operator_actions() -> None:
    document = build_domain_document_v2("HOME",timezone_code="Europe/Moscow")
    rows = [node for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.TABLE_ROW and node.node_id.startswith("home.operator.action.")]
    assert len(rows) == 5
    assert len({row.node_id for row in rows}) == len(rows)
    assert all(len(row.children) == 7 for row in rows)
    actions = [row.action for row in rows if row.action is not None]
    assert all(action.action_id in {"operator.decision.acknowledge", "operator.decision.measure", "operator.decision.refresh"} for action in actions)
    assert all(action.reversible and action.target_id and action.idempotency_key for action in actions)
    assert all(row.action is not None or row.children[6].content.message_key in {
        "home.operator.next.view", "home.operator.next.wait",
        "home.operator.next.automatic", "home.operator.next.review_block",
    } for row in rows)
    assert all(row.state.status_code in {"WARNING","BLOCKED"} for row in rows)
    assert all(row.state.quality_code == "UNVERIFIED" for row in rows)
    assert not [node for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.CARD and node.node_id.startswith("home.operator.action.")]
    header = next(node for node in _walk(document.root) if node.node_id == "home.operator.actions.table.header")
    assert [cell.content.message_key for cell in header.children] == [
        "column.operator.number", "column.operator.task", "column.operator.reason",
        "column.operator.effect", "column.operator.verdict",
        "column.operator.deadline", "column.operator.action",
    ]
    assert all(row.children[4].content.message_key.startswith("home.operator.status.") for row in rows)
    assert all(row.children[6].node_id.endswith(".next") for row in rows)


def test_expired_operator_decisions_remain_visible_but_disabled() -> None:
    resolver_source = Path("src/marketcore/presentation/workspace_v2/resolver/operator_decision_v2_resolver.py").read_text()
    presenter_source = Path("src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py").read_text()
    assert "WHERE expires_at > clock_timestamp()" not in resolver_source
    assert 'lifecycle_status = "MEASUREMENT_DUE"' in presenter_source
    assert 'else "NO_EFFECT"' in presenter_source
    assert '"DEGRADED" if actual_result is not None and actual_result < 0' in presenter_source
    assert "acknowledgeable = not expired" in presenter_source
    assert 'not blocked and str(item["selection_status"]) == "ACKNOWLEDGED"' in presenter_source
    assert "not expired and not blocked and str(item[\"selection_status\"]) == \"ACKNOWLEDGED\"" not in presenter_source


def test_operator_table_exposes_measured_results_and_lifecycle_actions() -> None:
    presenter_source = Path("src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py").read_text()
    renderer_source = Path("src/marketcore/presentation/workspace_v2/renderer/home_v2_domain_renderer.py").read_text()
    assert '"home.operator.field.actual_result"' in presenter_source
    assert '"operator.decision.refresh"' in presenter_source
    assert 'next_key = "home.operator.next.measure"' in renderer_source
    assert 'actual_value if actual_value is not None else effect_value' in renderer_source
    for status in ("MEASURING", "MEASUREMENT_DUE", "IMPROVED", "NO_EFFECT", "DEGRADED", "STALE"):
        assert f'"{status}"' in renderer_source or f'"{status}"' in presenter_source


def test_operator_table_uses_sequential_display_numbers() -> None:
    source = Path("src/marketcore/presentation/workspace_v2/renderer/home_v2_domain_renderer.py").read_text()
    assert "for display_number, card in enumerate(cards, start=1):" in source
    assert "value=display_number" in source
