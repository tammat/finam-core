from marketcore.presentation.render_tree.v2 import RenderNodeTypeV2
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def test_home_cards_show_operational_summaries_not_algorithm_dump() -> None:
    document = build_domain_document_v2("HOME", timezone_code="Europe/Moscow")
    nodes = {node.node_id: node for node in walk(document.root)}
    edge = nodes["home.operator.edge_search.primary_value"]
    model = nodes["home.operator.model_health.primary_value"]
    funnel = nodes["home.operator.signal_funnel.primary_value"]
    assert edge.content.message_key == "home.operator.edge_search.summary"
    assert "stage" in edge.content.message_args
    assert "algorithms" not in edge.content.message_args
    assert model.content.message_key == "home.operator.model_health.summary"
    assert funnel.content.message_key == "home.operator.signal_funnel.summary"


def test_operator_table_exposes_next_action() -> None:
    document = build_domain_document_v2("HOME", timezone_code="Europe/Moscow")
    nodes = list(walk(document.root))
    header = next(node for node in nodes if node.node_id == "home.operator.actions.table.header")
    assert header.children[-1].content.message_key == "column.operator.action"
    next_cells = [node for node in nodes if node.node_type is RenderNodeTypeV2.TABLE_CELL and node.node_id.endswith(".next")]
    assert next_cells
    assert all(cell.content.message_key in {
        "home.operator.next.open", "home.operator.next.wait", "home.operator.next.refresh"
    } for cell in next_cells)
