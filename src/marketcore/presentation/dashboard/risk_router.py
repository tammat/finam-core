from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from marketcore.presentation.pages.base_page import BaseDashboardPage, DashboardPageContext
from marketcore.services.risk.risk_control_center_service import RiskControlCenterService

risk_router = APIRouter()


class RiskControlCenterPage(BaseDashboardPage):
    page_key = "risk"
    title = "Риски"
    subtitle = "Risk Control Center"

    def __init__(self) -> None:
        self.vm = RiskControlCenterService().load()

    def render_body(self) -> str:
        return f"""
<section class="fc-card">
<h1>{self.title}</h1>
<p>{self.subtitle}</p>
</section>

<section class="fc-card">
<p>RISK_WIDGET_BINDING_V1</p>
</section>
"""


@risk_router.get("/risk", response_class=HTMLResponse)
def risk_page(
    lang: str = Query(default="ru"),
    timezone: str = Query(default="Europe/Moscow"),
):
    page = RiskControlCenterPage()
    return HTMLResponse(
        page.render(
            DashboardPageContext(
                lang=lang,
                timezone=timezone,
            )
        )
    )


@risk_router.get("/api/risk")
def risk_api():
    return asdict(RiskControlCenterService().load())
