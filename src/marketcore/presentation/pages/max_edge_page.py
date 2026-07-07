from __future__ import annotations

from marketcore.presentation.components import render_data_table, render_section
from marketcore.presentation.components.max_edge_card import render_max_edge_card
from marketcore.presentation.page import Page
from marketcore.presentation.providers.max_edge_provider import MaxEdgeProvider


class MaxEdgePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/max-edge",
            title="Max Edge",
            icon="🎯",
            menu_order=12,
        )

    def render(self) -> str:
        vm = MaxEdgeProvider().load(limit=20)
        return (
            render_max_edge_card(vm.current)
            + render_section(
                "Рейтинг edge",
                render_data_table(
                    [
                        "rank_no",
                        "symbol",
                        "strategy_code",
                        "timeframe",
                        "edge_score",
                        "confidence",
                        "net_after_tax",
                        "max_drawdown",
                        "trades",
                        "recommendation_code",
                    ],
                    vm.ranking,
                ),
            )
        )
