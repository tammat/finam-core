from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2
from marketcore.presentation.render_tree.v2 import ActionKindV2, RenderNodeTypeV2


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def test_every_functional_home_card_has_navigation_or_command() -> None:
    document = build_domain_document_v2("HOME")
    cards = [node for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.CARD]
    missing = [card.node_id for card in cards if card.action is None]
    assert missing == []
    assert all(card.action.action_kind in {ActionKindV2.NAVIGATE, ActionKindV2.COMMAND} for card in cards)


def test_home_card_targets_match_operating_modes() -> None:
    document = build_domain_document_v2("HOME")
    cards = {node.node_id: node for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.CARD}
    expected = {
        "home.profit_factory.roi": "container.capital",
        "home.card.system.status": "container.program",
        "home.card.status.portfolio": "container.portfolio",
        "home.card.status.research": "container.research",
        "home.card.status.runtime": "container.intraday",
        "home.card.probe": "container.intraday",
        "home.card.research": "container.research",
        "home.operator.recommendations": "container.research",
    }
    assert {node_id: cards[node_id].action.target_id for node_id in expected} == expected
