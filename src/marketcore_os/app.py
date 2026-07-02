from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from marketcore_os.layouts.base import APP_VERSION, normalize_lang, normalize_theme, render_shell
from marketcore_os.workspace.home import render_home_workspace

DEFAULT_LANG = "ru"
DEFAULT_TZ = "Europe/Moscow"
DEFAULT_CURRENCY = "RUB"
DEFAULT_THEME = "light"

app = FastAPI(title="MarketCore OS", version=APP_VERSION)


@app.get("/", response_class=HTMLResponse)
def workspace(request: Request) -> HTMLResponse:
    lang = normalize_lang(request.query_params.get("lang", DEFAULT_LANG))
    tz = request.query_params.get("tz", DEFAULT_TZ)
    currency = request.query_params.get("currency", DEFAULT_CURRENCY)
    theme = normalize_theme(request.query_params.get("theme", DEFAULT_THEME))

    content = render_home_workspace(lang)

    return HTMLResponse(
        render_shell(
            content=content,
            lang=lang,
            tz=tz,
            currency=currency,
            theme=theme,
        )
    )


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({
        "service": "marketcore-os",
        "status": "READY",
        "version": APP_VERSION,
        "home_workspace": "READY",
        "runtime_changed": 0,
        "execution_changed": 0,
        "orders_changed": 0,
        "fills_changed": 0,
        "micro_live_allowed": 0,
    })
