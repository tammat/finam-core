from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from marketcore.presentation.pages.base_page import BaseDashboardPage, DashboardPageContext
from marketcore.services.operations.operations_center_service import OperationsCenterService

operations_router = APIRouter()


class OperationsCenterPage(BaseDashboardPage):
    page_key = "operations"
    title = "Эксплуатация"
    subtitle = "Operations Center"

    def __init__(self) -> None:
        self.vm = OperationsCenterService().load()

    def render_body(self) -> str:
        return f"""
<section class="fc-card">
<h1>{self.title}</h1>
<p>{self.subtitle}</p>
</section>

<section class="fc-card">
<p>OPERATIONS_WIDGET_BINDING_V1</p>
</section>
"""


@operations_router.get("/operations", response_class=HTMLResponse)
def operations_page(
    lang: str = Query(default="ru"),
    timezone: str = Query(default="Europe/Moscow"),
):
    page = OperationsCenterPage()
    return HTMLResponse(
        page.render(
            DashboardPageContext(
                lang=lang,
                timezone=timezone,
            )
        )
    )


@operations_router.get("/api/operations")
def operations_api():
    return asdict(OperationsCenterService().load())
