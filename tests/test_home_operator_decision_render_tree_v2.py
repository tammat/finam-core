from marketcore.presentation.render_tree.v2 import RenderNodeTypeV2
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def test_home_exposes_ranked_non_green_operator_actions() -> None:
    document = build_domain_document_v2("HOME",timezone_code="Europe/Moscow")
    cards = [node for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.CARD and node.node_id.startswith("home.operator.action.")]
    assert len(cards) == 5
    assert all(card.action is None for card in cards)
    assert all(card.state.status_code in {"WARNING","BLOCKED"} for card in cards)
    assert all(card.state.quality_code == "UNVERIFIED" for card in cards)
    assert all(sum(child.node_type is RenderNodeTypeV2.METRIC_ROW for child in card.children) >= 11 for card in cards)
