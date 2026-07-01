from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from marketcore.presentation.dashboard.layout import render_shell
from marketcore.presentation.dashboard.services import get_framework_status

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(
    lang: str = Query(default="ru"),
    timezone: str = Query(default="Europe/Moscow"),
) -> HTMLResponse:
    status = get_framework_status()
    content = f"""
    <section class="card">
      <h1>Dashboard Framework V1</h1>
      <p>Status: <strong>{status["status"]}</strong></p>
      <p>Backend: {status["backend"]}</p>
      <p>Templates: {status["templates"]}</p>
      <p>Dynamic UI: {status["dynamic_ui"]}</p>
    </section>
    """
    return HTMLResponse(render_shell(content, lang=lang, timezone=timezone))


@router.get("/{page_key}", response_class=HTMLResponse)
def placeholder_page(
    page_key: str,
    lang: str = Query(default="ru"),
    timezone: str = Query(default="Europe/Moscow"),
) -> HTMLResponse:
    content = f"""
    <section class="card">
      <h1>{page_key.upper()}</h1>
      <p>Page placeholder: READY</p>
    </section>
    """
    return HTMLResponse(render_shell(content, lang=lang, timezone=timezone))
