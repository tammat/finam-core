from __future__ import annotations

from marketcore.presentation.page import Page
from marketcore.presentation.providers.edge_score_shadow_daily_provider import (
    EdgeScoreShadowDailyProvider,
)
from marketcore.presentation.components.edge_score_shadow_daily_card import (
    render_edge_score_shadow_daily_card,
)


class EdgeScoreShadowDailyPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-score-shadow-daily",
            title="edge.score.shadow.daily.title",
            icon="📊",
            menu_order=14,
        )

    def render(self) -> str:
        vm = EdgeScoreShadowDailyProvider().load(limit=50)
        return render_edge_score_shadow_daily_card(vm)
