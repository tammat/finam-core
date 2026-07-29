from marketcore.presentation.render_tree.v2 import RenderNodeTypeV2
from marketcore.presentation.workspace_v2.presenter.home_v2_presenter import HomeV2Presenter
from marketcore.presentation.workspace_v2.renderer.home_v2_domain_renderer import render_home_domain_v2


def build_legacy_home():
    return render_home_domain_v2(HomeV2Presenter().load(), timezone_code="Europe/Moscow")


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def test_home_cards_show_operational_summaries_not_algorithm_dump() -> None:
    document = build_legacy_home()
    nodes = {node.node_id: node for node in walk(document.root)}
    edge = nodes["home.operator.edge_search.primary_value"]
    model = nodes["home.operator.model_health.primary_value"]
    funnel = nodes["home.operator.signal_funnel.primary_value"]
    assert edge.content.message_key == "home.operator.edge_search.summary"
    assert "stage" in edge.content.message_args
    assert "algorithms" not in edge.content.message_args
    assert model.content.message_key == "home.operator.model_health.summary"
    assert funnel.content.message_key == "home.operator.signal_funnel.summary"
    loss = nodes["home.operator.main_loss.primary_value"]
    solution = nodes["home.operator.loss_solution.primary_value"]
    assert loss.content.message_key == "home.operator.main_loss.summary"
    assert solution.content.message_key == "home.operator.loss_solution.summary"
    diagnostic = nodes["home.operator.diagnostic_funnels.primary_value"]
    assert diagnostic.content.message_key == "home.operator.diagnostic_funnels.summary"


def test_operator_table_exposes_next_action() -> None:
    document = build_legacy_home()
    nodes = list(walk(document.root))
    header = next(node for node in nodes if node.node_id == "home.operator.actions.table.header")
    assert header.children[-1].content.message_key == "column.operator.action"
    next_cells = [node for node in nodes if node.node_type is RenderNodeTypeV2.TABLE_CELL and node.node_id.endswith(".next")]
    assert next_cells
    assert all(cell.content.message_key in {
        "home.operator.next.open", "home.operator.next.wait", "home.operator.next.view",
        "home.operator.next.measure", "home.operator.next.refresh",
    } for cell in next_cells)
