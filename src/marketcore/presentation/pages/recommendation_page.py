from __future__ import annotations

import json
from pathlib import Path

from marketcore.presentation.components import render_data_table, render_kpi_card, render_object_card, render_section
from marketcore.presentation.page import Page


class RecommendationPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/recommendation",
            title="Recommendation",
            icon="🎯",
            menu_order=49,
        )

    def render(self) -> str:
        path = Path("reports/recommendation_engine_latest.json")
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

        strategies = data.get("focus_strategies", [])
        symbols = data.get("focus_symbols", [])
        timeframes = data.get("focus_timeframes", [])
        drops = data.get("temporary_drop_symbols", [])

        kpi = "".join([
            render_kpi_card("Действие", data.get("primary_action", "NO_DATA"), "recommendation"),
            render_kpi_card("Стратегии", len(strategies), "focus_strategies"),
            render_kpi_card("Инструменты", len(symbols), "focus_symbols"),
            render_kpi_card("Timeframes", len(timeframes), "focus_timeframes"),
        ])

        rows = []
        for strategy in strategies:
            for symbol in symbols:
                rows.append({
                    "action": "EXPAND",
                    "strategy": strategy,
                    "symbol": symbol,
                    "timeframes": ", ".join(timeframes),
                })

        cards = "".join([
            render_object_card("Primary recommendation", {
                "Action": data.get("primary_action", ""),
                "Next epic": data.get("next_epic", ""),
                "Drop temporary": ", ".join(drops),
            })
        ])

        table = render_data_table(
            ["action", "strategy", "symbol", "timeframes"],
            rows,
        )

        return (
            render_section("Recommendation", kpi)
            + render_section("Карточка решения", cards)
            + render_section("План исследований", table)
        )
