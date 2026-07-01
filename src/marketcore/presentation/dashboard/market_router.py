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
        vm = self.vm

        from marketcore.presentation.widgets.market_page.overview import MarketOverviewWidget
        from marketcore.presentation.widgets.market_page.quality import MarketQualityWidget
        from marketcore.presentation.widgets.market_page.instruments import MarketInstrumentsWidget
        from marketcore.presentation.widgets.market_page.actions import MarketActionsWidget

        widgets = [
            MarketOverviewWidget(),
            MarketQualityWidget(),
            MarketInstrumentsWidget(),
            MarketActionsWidget(),
        ]

        header = (
            '<section class="fc-card">'
            f'<h1>{self.title}</h1>'
            f'<p>{self.subtitle}</p>'
            '</section>'
        )

        return header + "".join(widget.render(vm) for widget in widgets)


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
