from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from marketcore.presentation.dashboard.layout import render_shell
from marketcore.presentation.dashboard.preview_service import (
    build_component_preview_html,
    get_component_preview_status,
)

preview_router = APIRouter()


@preview_router.get("/components", response_class=HTMLResponse)
def component_preview(
    lang: str = Query(default="ru"),
    timezone: str = Query(default="Europe/Moscow"),
) -> HTMLResponse:
    return HTMLResponse(
        render_shell(
            build_component_preview_html(),
            lang=lang,
            timezone=timezone,
        )
    )


@preview_router.get("/api/components")
def component_preview_status() -> dict[str, object]:
    return get_component_preview_status()
