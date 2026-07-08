from __future__ import annotations

from marketcore.presentation.page_contract import Page
from marketcore.presentation.providers.edge_score_shadow_observation_provider import (
    EdgeScoreShadowObservationProvider,
)
from marketcore.presentation.components.edge_score_shadow_observation_card import (
    render_edge_score_shadow_observation_card,
)


def render() -> str:
    vm = EdgeScoreShadowObservationProvider().load(limit=50)
    return render_edge_score_shadow_observation_card(vm)


page = Page(
    route="/edge-score-shadow",
    title="edge.score.shadow.title",
    render=render,
)
