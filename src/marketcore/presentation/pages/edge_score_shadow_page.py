from __future__ import annotations

from marketcore.presentation.page import Page
from marketcore.presentation.providers.edge_score_shadow_observation_provider import (
    EdgeScoreShadowObservationProvider,
)
from marketcore.presentation.components.edge_score_shadow_observation_card import (
    render_edge_score_shadow_observation_card,
)


class EdgeScoreShadowPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-score-shadow",
            title="edge.score.shadow.title",
            icon="👁️",
            menu_order=13,
        )

    def render(self) -> str:
        vm = EdgeScoreShadowObservationProvider().load(limit=50)
        return render_edge_score_shadow_observation_card(vm)
