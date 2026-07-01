from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from marketcore.presentation.pages.base_page import (
    BaseDashboardPage,
    DashboardPageContext,
)
from marketcore.presentation.dashboard.layout import render_shell
from marketcore.services.market.market_intelligence_service import (
    MarketIntelligenceService,
)

market_router = APIRouter()


class MarketIntelligencePage(BaseDashboardPage):
    page_key = "market"
    title = "Рынок"
    subtitle = "Market Intelligence"

    def __init__(self) -> None:
        self.vm = MarketIntelligenceService().load()

    def render_body(self) -> str:
        return f"""
<section class="fc-card">
<h1>{self.title}</h1>
<p>{self.subtitle}</p>
</section>

<section class="fc-card">
<p>MARKET_WIDGET_BINDING_V1</p>
</section>
"""


@market_router.get("/market", response_class=HTMLResponse)
def market_page(
    lang: str = Query(default="ru"),
    timezone: str = Query(default="Europe/Moscow"),
):
    page = MarketIntelligencePage()

    return HTMLResponse(
        page.render(
            DashboardPageContext(
                lang=lang,
                timezone=timezone,
            )
        )
    )


@market_router.get("/api/market")
def market_api():
    return asdict(
        MarketIntelligenceService().load()
    )
