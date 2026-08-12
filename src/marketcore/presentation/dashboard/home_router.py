from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from marketcore.presentation.pages.base_page import BaseDashboardPage, DashboardPageContext
from marketcore.services.dashboard.executive_overview_service import ExecutiveOverviewService

home_router = APIRouter()


class ExecutiveOverviewPage(BaseDashboardPage):
    page_key = "executive_overview"
    title = "MarketCore"
    subtitle = "Trading Intelligence Platform v1.0.0"

    def __init__(self) -> None:
        self.vm = ExecutiveOverviewService().load()

    def render_body(self) -> str:
        from marketcore.presentation.widgets.home_page.edge_search import (
            HomeEdgeSearchWidget,
        )
        from marketcore.services.research.research_center_service import (
            ResearchCenterService,
        )
        vm = self.vm

        from importlib import import_module

        def optional_widget(
            module_name: str,
            class_name: str,
        ):
            try:
                module = import_module(module_name)
            except ModuleNotFoundError:
                return None
            return getattr(module, class_name, None)

        optional_widget_specs = (
            (
                "marketcore.presentation.widgets.executive_health.renderer",
                "ExecutiveHealthWidget",
            ),
            (
                "marketcore.presentation.widgets.platform_status.renderer",
                "PlatformStatusWidget",
            ),
            (
                "marketcore.presentation.widgets.market_summary.renderer",
                "MarketSummaryWidget",
            ),
            (
                "marketcore.presentation.widgets.research_summary.renderer",
                "ResearchSummaryWidget",
            ),
            (
                "marketcore.presentation.widgets.metadata_summary.renderer",
                "MetadataSummaryWidget",
            ),
            (
                "marketcore.presentation.widgets.risk_summary.renderer",
                "RiskSummaryWidget",
            ),
            (
                "marketcore.presentation.widgets.execution_summary.renderer",
                "ExecutionSummaryWidget",
            ),
            (
                "marketcore.presentation.widgets.version_summary.renderer",
                "VersionSummaryWidget",
            ),
            (
                "marketcore.presentation.widgets.activity_summary.renderer",
                "ActivitySummaryWidget",
            ),
            (
                "marketcore.presentation.widgets.quick_actions.renderer",
                "QuickActionsWidget",
            ),
        )

        frontier = ResearchCenterService().load().frontier

        widgets = [
            HomeEdgeSearchWidget(),
        ]

        for module_name, class_name in optional_widget_specs:
            widget_class = optional_widget(
                module_name,
                class_name,
            )
            if widget_class is not None:
                widgets.append(widget_class())

        header = (
            '<section class="fc-card">'
            f'<h1>{self.title}</h1>'
            f'<p>{self.subtitle}</p>'
            '</section>'
        )

        return header + "".join(
            widget.render(frontier)
            if isinstance(widget, HomeEdgeSearchWidget)
            else widget.render(vm)
            for widget in widgets
        )


@home_router.get("/", response_class=HTMLResponse)
def executive_overview(
    lang: str = Query(default="ru"),
    timezone: str = Query(default="Europe/Moscow"),
) -> HTMLResponse:
    page = ExecutiveOverviewPage()
    return HTMLResponse(
        page.render(
            DashboardPageContext(
                lang=lang,
                timezone=timezone,
            )
        )
    )


@home_router.get("/api/home")
def executive_overview_api() -> dict[str, object]:
    vm = ExecutiveOverviewService().load()
    return asdict(vm)
