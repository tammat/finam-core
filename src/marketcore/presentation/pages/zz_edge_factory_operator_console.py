from __future__ import annotations

from marketcore.presentation.components import render_data_table, render_object_card, render_section
from marketcore.presentation.components.discovery_action_panel import render_action_panel
from marketcore.presentation.components.max_edge_card import render_max_edge_card
from marketcore.presentation.page import Page
from marketcore.presentation.providers.edge_factory_console_provider import EdgeFactoryConsoleProvider


class EdgeFactoryOperatorConsolePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-factory",
            title="Edge Factory",
            icon="🏭",
            menu_order=10,
        )

    def render(self) -> str:
        vm = EdgeFactoryConsoleProvider().load()
        current_edge = vm["max_edge"][0] if vm["max_edge"] else {}

        bottleneck_card = render_object_card("Узкое место", {
            "stage": vm["bottleneck"].get("pipeline_stage", ""),
            "conversion_pct": vm["bottleneck"].get("conversion_pct", ""),
            "severity": vm["bottleneck"].get("severity", ""),
            "root_cause": vm["bottleneck"].get("root_cause_code", ""),
            "recommendation": vm["bottleneck"].get("recommendation_code", ""),
            "expected_gain_pct": vm["bottleneck"].get("expected_gain_pct", ""),
        })

        return (
            render_section("Edge Factory", render_max_edge_card(current_edge))
            + render_section("Узкое место", bottleneck_card)
            + render_section("Действия", render_action_panel(vm["actions"]))
            + render_section("Очередь Discovery", render_data_table(["status", "rows"], vm["queue"]))
            + render_section("Команды", render_data_table(["command_status", "rows"], vm["commands"]))
            + render_section(
                "Рейтинг edge",
                render_data_table(
                    ["rank_no", "symbol", "strategy_code", "timeframe", "edge_score", "confidence", "trades", "recommendation_code"],
                    vm["max_edge"],
                ),
            )
        )
