from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from marketcore.presentation.pages.base_page import BaseDashboardPage, DashboardPageContext
from marketcore.services.research.research_center_service import ResearchCenterService

research_router = APIRouter()


class ResearchCenterPage(BaseDashboardPage):
    page_key = "research"
    title = "Исследования"
    subtitle = "Research Center"

    def __init__(self) -> None:
        self.vm = ResearchCenterService().load()

    def render_body(self) -> str:
        vm = self.vm

        from marketcore.presentation.widgets.research_page.overview import ResearchOverviewWidget
        from marketcore.presentation.widgets.research_page.candidates import ResearchCandidatesWidget
        from marketcore.presentation.widgets.research_page.checks import ResearchChecksWidget
        from marketcore.presentation.widgets.research_page.edge_validation import ResearchEdgeValidationWidget
        from marketcore.presentation.widgets.research_page.actions import ResearchActionsWidget

        widgets = [
            ResearchOverviewWidget(),
            ResearchCandidatesWidget(),
            ResearchChecksWidget(),
            ResearchEdgeValidationWidget(),
            ResearchActionsWidget(),
        ]

        header = (
            '<section class="fc-card">'
            f'<h1>{self.title}</h1>'
            f'<p>{self.subtitle}</p>'
            '</section>'
        )

        return header + "".join(widget.render(vm) for widget in widgets)


@research_router.get("/research", response_class=HTMLResponse)
def research_page(
    lang: str = Query(default="ru"),
    timezone: str = Query(default="Europe/Moscow"),
):
    page = ResearchCenterPage()
    return HTMLResponse(
        page.render(
            DashboardPageContext(
                lang=lang,
                timezone=timezone,
            )
        )
    )


@research_router.get("/api/research")
def research_api():
    return asdict(ResearchCenterService().load())
