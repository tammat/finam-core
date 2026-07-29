from marketcore.presentation.render_tree.v2 import ActionKindV2, RenderNodeTypeV2
from marketcore.presentation.workspace_v2.presenter.home_v2_presenter import HomeV2Presenter
from marketcore.presentation.workspace_v2.renderer.home_v2_domain_renderer import render_home_domain_v2


def build_legacy_home():
    return render_home_domain_v2(HomeV2Presenter().load(), timezone_code="Europe/Moscow")


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def test_operator_dashboard_cards_navigate_to_registered_modes(monkeypatch) -> None:
    monkeypatch.setenv("MARKETCORE_HOME_CLEAN_MODE", "0")
    document = build_legacy_home()
    cards = {
        node.node_id: node
        for node in _walk(document.root)
        if node.node_type is RenderNodeTypeV2.CARD and node.node_id.startswith("home.operator.")
    }
    expected = {
        "home.operator.model_health": "container.program",
        "home.operator.recommendations": "container.research",
        "home.operator.edge_search": "container.research",
        "home.operator.signal_funnel": "container.edge",
        "home.operator.risk": "container.risk",
        "home.operator.events": "container.program",
    }
    assert expected.keys() <= cards.keys()
    for node_id, target_id in expected.items():
        assert cards[node_id].action is not None
        assert cards[node_id].action.action_kind is ActionKindV2.NAVIGATE
        assert cards[node_id].action.target_id == target_id
