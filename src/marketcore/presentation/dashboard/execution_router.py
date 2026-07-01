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
        return f"""
<section class="fc-card">
<h1>{self.title}</h1>
<p>{self.subtitle}</p>
</section>

<section class="fc-card">
<p>EXECUTION_WIDGET_BINDING_V1</p>
</section>
"""


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
