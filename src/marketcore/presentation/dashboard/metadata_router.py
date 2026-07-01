from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from marketcore.presentation.pages.base_page import BaseDashboardPage, DashboardPageContext
from marketcore.services.metadata.metadata_center_service import MetadataCenterService

metadata_router = APIRouter()


class MetadataCenterPage(BaseDashboardPage):
    page_key = "metadata"
    title = "Метаданные"
    subtitle = "Metadata Center"

    def __init__(self) -> None:
        self.vm = MetadataCenterService().load()

    def render_body(self) -> str:
        return f"""
<section class="fc-card">
<h1>{self.title}</h1>
<p>{self.subtitle}</p>
</section>

<section class="fc-card">
<p>METADATA_WIDGET_BINDING_V1</p>
</section>
"""


@metadata_router.get("/metadata", response_class=HTMLResponse)
def metadata_page(
    lang: str = Query(default="ru"),
    timezone: str = Query(default="Europe/Moscow"),
):
    page = MetadataCenterPage()
    return HTMLResponse(
        page.render(
            DashboardPageContext(
                lang=lang,
                timezone=timezone,
            )
        )
    )


@metadata_router.get("/api/metadata")
def metadata_api():
    return asdict(MetadataCenterService().load())
