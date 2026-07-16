from marketcore.presentation.render_tree.v2 import RenderNodeTypeV2
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def test_home_exposes_ranked_non_green_operator_actions() -> None:
    document = build_domain_document_v2("HOME",timezone_code="Europe/Moscow")
    rows = [node for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.TABLE_ROW and node.node_id.startswith("home.operator.action.")]
    assert 1 <= len(rows) <= 5
    assert len({row.node_id for row in rows}) == len(rows)
    assert all(len(row.children) == 7 for row in rows)
    actions = [row.action for row in rows if row.action is not None]
    assert actions
    assert all(action.action_id in {"operator.decision.acknowledge", "operator.decision.measure"} for action in actions)
    assert all(action.reversible and action.target_id and action.idempotency_key for action in actions)
    assert all(row.state.status_code in {"WARNING","BLOCKED"} for row in rows)
    assert all(row.state.quality_code == "UNVERIFIED" for row in rows)
    assert not [node for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.CARD and node.node_id.startswith("home.operator.action.")]
    header = next(node for node in _walk(document.root) if node.node_id == "home.operator.actions.table.header")
    assert [cell.content.message_key for cell in header.children] == [
        "column.operator.number", "column.operator.action", "column.operator.reason",
        "column.operator.effect", "column.operator.confidence",
        "column.operator.verdict", "column.operator.deadline",
    ]
