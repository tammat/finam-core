from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from marketcore.presentation.pages.base_page import BaseDashboardPage, DashboardPageContext
from marketcore.services.execution.execution_center_service import ExecutionCenterService

execution_router = APIRouter()


class ExecutionCenterPage(BaseDashboardPage):
    page_key = "execution"
    title = "Выполнение"
    subtitle = "Execution Center"

    def __init__(self) -> None:
        self.vm = ExecutionCenterService().load()

    def render_body(self) -> str:
        vm = self.vm

        from marketcore.presentation.widgets.execution_page.overview import ExecutionOverviewWidget
        from marketcore.presentation.widgets.execution_page.orders import ExecutionOrdersWidget
        from marketcore.presentation.widgets.execution_page.fills import ExecutionFillsWidget
        from marketcore.presentation.widgets.execution_page.actions import ExecutionActionsWidget

        widgets = [
            ExecutionOverviewWidget(),
            ExecutionOrdersWidget(),
            ExecutionFillsWidget(),
            ExecutionActionsWidget(),
        ]

        header = (
            '<section class="fc-card">'
            f'<h1>{self.title}</h1>'
            f'<p>{self.subtitle}</p>'
            '</section>'
        )

        return header + "".join(widget.render(vm) for widget in widgets)


@execution_router.get("/execution", response_class=HTMLResponse)
def execution_page(
    lang: str = Query(default="ru"),
    timezone: str = Query(default="Europe/Moscow"),
):
    page = ExecutionCenterPage()
    return HTMLResponse(
        page.render(
            DashboardPageContext(
                lang=lang,
                timezone=timezone,
            )
        )
    )


@execution_router.get("/api/execution")
def execution_api():
    return asdict(ExecutionCenterService().load())
