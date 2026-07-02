from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from marketcore_os.layouts.base import APP_VERSION, normalize_lang, normalize_theme, render_shell
from marketcore_os.workspace.home import render_home_workspace
from marketcore_os.workspace.capital import render_capital_workspace
from marketcore_os.workspace.research import render_research_workspace
from marketcore_os.workspace.edge import render_edge_workspace
from marketcore_os.services.capital import CapitalService
from marketcore_os.services.profit import ProfitService
from marketcore_os.services.research import ResearchService
from marketcore_os.services.risk import RiskService
from marketcore_os.services.program import ProgramService

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


@app.get("/api/v1/research/widget")
def research_widget_api() -> JSONResponse:
    vm = ResearchService().get_widget_model()
    return JSONResponse({
        "pipeline_status": vm.pipeline_status,
        "top3_status": vm.top3_status,
        "edge_factory_status": vm.edge_factory_status,
        "research_candidates": vm.research_candidates,
        "oos_pass": vm.oos_pass,
        "paper_ready": vm.paper_ready,
        "data_source": vm.data_source,
        "runtime_changed": 0,
        "execution_changed": 0,
        "orders_changed": 0,
        "fills_changed": 0,
        "micro_live_allowed": 0,
    })


@app.get("/api/v1/risk/widget")
def risk_widget_api() -> JSONResponse:
    vm = RiskService().get_widget_model()
    return JSONResponse({
        "runtime_allowed": vm.runtime_allowed,
        "execution_allowed": vm.execution_allowed,
        "micro_live_allowed": vm.micro_live_allowed,
        "daily_risk_pct": str(vm.daily_risk_pct),
        "risk_status": vm.risk_status,
        "data_source": vm.data_source,
        "runtime_changed": 0,
        "execution_changed": 0,
        "orders_changed": 0,
        "fills_changed": 0,
        "micro_live_allowed_flag": 0,
    })


@app.get("/capital", response_class=HTMLResponse)
def capital_workspace(request: Request) -> HTMLResponse:
    lang = normalize_lang(request.query_params.get("lang", DEFAULT_LANG))
    tz = request.query_params.get("tz", DEFAULT_TZ)
    currency = request.query_params.get("currency", DEFAULT_CURRENCY)
    theme = normalize_theme(request.query_params.get("theme", DEFAULT_THEME))

    content = render_capital_workspace(lang, currency)

    return HTMLResponse(
        render_shell(
            content=content,
            lang=lang,
            tz=tz,
            currency=currency,
            theme=theme,
        )
    )


@app.get("/api/v1/program/widget")
def program_widget_api() -> JSONResponse:
    vm = ProgramService().get_widget_model()
    return JSONResponse({
        "quarter": vm.quarter,
        "platform_status": vm.platform_status,
        "research_status": vm.research_status,
        "top3_status": vm.top3_status,
        "paper_status": vm.paper_status,
        "marketcore_status": vm.marketcore_status,
        "data_source": vm.data_source,
        "runtime_changed": 0,
        "execution_changed": 0,
        "orders_changed": 0,
        "fills_changed": 0,
        "micro_live_allowed": 0,
    })


@app.get("/research", response_class=HTMLResponse)
def research_workspace(request: Request):

    lang = normalize_lang(request.query_params.get("lang", DEFAULT_LANG))
    tz = request.query_params.get("tz", DEFAULT_TZ)
    currency = request.query_params.get("currency", DEFAULT_CURRENCY)
    theme = normalize_theme(request.query_params.get("theme", DEFAULT_THEME))

    return HTMLResponse(
        render_shell(
            content=render_research_workspace(lang),
            lang=lang,
            tz=tz,
            currency=currency,
            theme=theme,
        )
    )


@app.get("/edge",response_class=HTMLResponse)
def edge_workspace(request:Request):

    lang=normalize_lang(request.query_params.get("lang",DEFAULT_LANG))
    tz=request.query_params.get("tz",DEFAULT_TZ)
    currency=request.query_params.get("currency",DEFAULT_CURRENCY)
    theme=normalize_theme(request.query_params.get("theme",DEFAULT_THEME))

    return HTMLResponse(

        render_shell(

            content=render_edge_workspace(lang),

            lang=lang,

            tz=tz,

            currency=currency,

            theme=theme

        )

    )

