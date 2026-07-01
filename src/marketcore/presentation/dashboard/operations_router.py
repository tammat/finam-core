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
        vm = self.vm

        from marketcore.presentation.widgets.operations_page.overview import OperationsOverviewWidget
        from marketcore.presentation.widgets.operations_page.services import OperationsServicesWidget
        from marketcore.presentation.widgets.operations_page.events import OperationsEventsWidget
        from marketcore.presentation.widgets.operations_page.actions import OperationsActionsWidget

        widgets = [
            OperationsOverviewWidget(),
            OperationsServicesWidget(),
            OperationsEventsWidget(),
            OperationsActionsWidget(),
        ]

        header = (
            '<section class="fc-card">'
            f'<h1>{self.title}</h1>'
            f'<p>{self.subtitle}</p>'
            '</section>'
        )

        return header + "".join(widget.render(vm) for widget in widgets)


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
