from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from marketcore_os.layouts.base import APP_VERSION, normalize_lang, normalize_theme, render_shell
from marketcore_os.workspace.home import render_home_workspace
from marketcore_os.services.capital import CapitalService
from marketcore_os.services.profit import ProfitService

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


@app.get("/api/v1/capital/widget")
def capital_widget_api() -> JSONResponse:
    vm = CapitalService().get_widget_model(display_currency="RUB")
    return JSONResponse({
        "planned_capital": str(vm.planned_capital),
        "working_capital": str(vm.working_capital),
        "available_capital": str(vm.available_capital),
        "working_pct": str(vm.working_pct.quantize(__import__("decimal").Decimal("0.01"))),
        "available_pct": str(vm.available_pct.quantize(__import__("decimal").Decimal("0.01"))),
        "today_pnl": str(vm.today_pnl),
        "base_currency": vm.base_currency,
        "display_currency": vm.display_currency,
        "fx_source": vm.fx_source,
        "data_source": vm.data_source,
        "runtime_changed": 0,
        "execution_changed": 0,
        "orders_changed": 0,
        "fills_changed": 0,
        "micro_live_allowed": 0,
    })


@app.get("/api/v1/profit/widget")
def profit_widget_api() -> JSONResponse:
    vm = ProfitService().get_widget_model()
    return JSONResponse({
        "production_edges": vm.production_edges,
        "paper_edges": vm.paper_edges,
        "shadow_edges": vm.shadow_edges,
        "research_candidates": vm.research_candidates,
        "paper_status": vm.paper_status,
        "shadow_status": vm.shadow_status,
        "data_source": vm.data_source,
        "runtime_changed": 0,
        "execution_changed": 0,
        "orders_changed": 0,
        "fills_changed": 0,
        "micro_live_allowed": 0,
    })
