from marketcore.presentation.workspace_v2.presenter.home_v2_presenter import HomeV2Presenter
from marketcore.presentation.workspace_v2.renderer.home_v2_domain_renderer import render_home_domain_v2


def build_legacy_home():
    return render_home_domain_v2(HomeV2Presenter().load(), timezone_code="Europe/Moscow")
from marketcore.presentation.render_tree.v2 import ActionKindV2, RenderNodeTypeV2


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def test_every_functional_home_card_has_navigation_or_command() -> None:
    document = build_legacy_home()
    cards = [node for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.CARD]
    missing = [card.node_id for card in cards if card.action is None]
    assert missing == []
    assert all(card.action.action_kind in {ActionKindV2.NAVIGATE, ActionKindV2.COMMAND} for card in cards)


def test_home_card_targets_match_operating_modes() -> None:
    document = build_legacy_home()
    cards = {node.node_id: node for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.CARD}
    expected = {
        "home.traffic.data": "container.research",
        "home.traffic.edge": "container.edge",
        "home.traffic.forward": "container.intraday",
        "home.traffic.execution": "container.intraday",
        "home.traffic.live": "container.edge",
        "home.operator.model_health": "container.program",
        "home.operator.edge_search": "container.research",
        "home.operator.signal_funnel": "container.edge",
        "home.operator.diagnostic_funnels": "container.research",
        "home.operator.main_loss": "container.research",
        "home.operator.loss_solution": "container.research",
    }
    assert {node_id: cards[node_id].action.target_id for node_id in expected} == expected
