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
        vm = self.vm

        from marketcore.presentation.widgets.executive_health.renderer import ExecutiveHealthWidget
        from marketcore.presentation.widgets.platform_status.renderer import PlatformStatusWidget
        from marketcore.presentation.widgets.market_summary.renderer import MarketSummaryWidget
        from marketcore.presentation.widgets.research_summary.renderer import ResearchSummaryWidget
        from marketcore.presentation.widgets.metadata_summary.renderer import MetadataSummaryWidget
        from marketcore.presentation.widgets.risk_summary.renderer import RiskSummaryWidget
        from marketcore.presentation.widgets.execution_summary.renderer import ExecutionSummaryWidget
        from marketcore.presentation.widgets.version_summary.renderer import VersionSummaryWidget
        from marketcore.presentation.widgets.activity_summary.renderer import ActivitySummaryWidget
        from marketcore.presentation.widgets.quick_actions.renderer import QuickActionsWidget

        widgets = [
            ExecutiveHealthWidget(),
            PlatformStatusWidget(),
            MarketSummaryWidget(),
            ResearchSummaryWidget(),
            MetadataSummaryWidget(),
            RiskSummaryWidget(),
            ExecutionSummaryWidget(),
            VersionSummaryWidget(),
            ActivitySummaryWidget(),
            QuickActionsWidget(),
        ]

        header = (
            '<section class="fc-card">'
            f'<h1>{self.title}</h1>'
            f'<p>{self.subtitle}</p>'
            '</section>'
        )

        return header + "".join(widget.render(vm) for widget in widgets)


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
