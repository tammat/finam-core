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
        return f"""
<section class="fc-card">
<h1>{self.title}</h1>
<p>{self.subtitle}</p>
</section>

<section class="fc-card">
<p>RESEARCH_WIDGET_BINDING_V1</p>
</section>
"""


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
