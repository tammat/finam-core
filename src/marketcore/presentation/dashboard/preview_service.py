from __future__ import annotations

from marketcore.presentation.design_system.components.badges import Badge
from marketcore.presentation.design_system.components.cards import (
    HealthCard,
    KeyValueCard,
    MetricCard,
    StatusCard,
    VersionCard,
)
from marketcore.presentation.design_system.components.heatmap import HeatmapCard
from marketcore.presentation.design_system.components.tables import TableCard
from marketcore.presentation.design_system.components.timeline import TimelineCard
from marketcore.presentation.design_system.foundation.tokens import BREAKPOINTS, RADIUS, SPACING, STATUS_COLORS
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.design_system.registry import design_registry


def build_component_preview_html() -> str:
    registry_rows = [
        [component.name, component.category, component.status]
        for component in sorted(design_registry.list(), key=lambda c: c.name)
    ]

    cards = [
        HealthCard("System Health", "READY"),
        MetricCard("Market Bars", 875706, "READY"),
        StatusCard("Correlation Risk", "HIGH"),
        VersionCard("Metadata Version", "1.0.0"),
        KeyValueCard("Metadata", {"Coverage": "100%", "Objects": 373, "Sources": 12}),
    ]

    foundation = KeyValueCard(
        "Foundation Tokens",
        {
            "Colors": len(STATUS_COLORS),
            "Spacing": len(SPACING),
            "Radius": len(RADIUS),
            "Breakpoints": len(BREAKPOINTS),
        },
    )

    responsive = KeyValueCard(
        "Responsive Breakpoints",
        {
            "Phone": BREAKPOINTS["PHONE"],
            "Tablet": BREAKPOINTS["TABLET"],
            "Notebook": BREAKPOINTS["NOTEBOOK"],
            "Desktop": BREAKPOINTS["DESKTOP"],
        },
    )

    return "".join(
        [
            SectionHeader("Dashboard Component Preview"),
            DashboardGrid([foundation, responsive]),
            SectionHeader("Cards"),
            DashboardGrid(cards),
            SectionHeader("Badges"),
            DashboardGrid(
                [
                    KeyValueCard(
                        "Statuses",
                        {
                            "READY": Badge("READY", "READY"),
                            "WARNING": Badge("WARNING", "WARNING"),
                            "HIGH": Badge("HIGH", "HIGH"),
                            "CRITICAL": Badge("CRITICAL", "CRITICAL"),
                            "DISABLED": Badge("DISABLED", "DISABLED"),
                            "INFO": Badge("INFO", "INFO"),
                        },
                    )
                ]
            ),
            SectionHeader("Table"),
            TableCard(
                "Market Data",
                ["Object", "Rows", "Status"],
                [
                    ["market_bars", 875706, "READY"],
                    ["market_ticks", 71098524, "READY"],
                    ["normalized_bar_event_v1", 0, "EMPTY_NOT_BUILT"],
                ],
            ),
            SectionHeader("Timeline"),
            TimelineCard(
                "Activity",
                [
                    {"time": "09:00", "text": "Dashboard Framework ready"},
                    {"time": "09:10", "text": "Dashboard Layout ready"},
                    {"time": "09:20", "text": "Design System ready"},
                ],
            ),
            SectionHeader("Heatmap"),
            HeatmapCard(
                "Risk Heatmap",
                {
                    "Architecture": "READY",
                    "Market Data": "READY",
                    "Correlation": "HIGH",
                    "Runtime": "READY",
                },
            ),
            SectionHeader("Registry"),
            TableCard(
                "Registered Components",
                ["Name", "Category", "Status"],
                registry_rows,
            ),
        ]
    )


def get_component_preview_status() -> dict[str, object]:
    return {
        "name": "DASHBOARD_COMPONENT_PREVIEW_V1",
        "status": "READY",
        "component_count": len(design_registry.list()),
        "runtime_changed": 0,
        "execution_changed": 0,
        "orders_changed": 0,
        "fills_changed": 0,
        "micro_live_allowed": 0,
    }
