from __future__ import annotations

from fastapi import FastAPI

from marketcore.presentation.dashboard.api import api_router
from marketcore.presentation.dashboard.router import router
from marketcore.presentation.dashboard.preview_router import preview_router
from marketcore.presentation.dashboard.home_router import home_router
from marketcore.presentation.dashboard.market_router import market_router
from marketcore.presentation.dashboard.research_router import research_router
from marketcore.presentation.dashboard.metadata_router import metadata_router
from marketcore.presentation.dashboard.risk_router import risk_router
from marketcore.presentation.dashboard.execution_router import execution_router

app = FastAPI(title="MarketCore Dashboard", version="1.0.0")

app.include_router(api_router)
app.include_router(preview_router)
app.include_router(home_router)
app.include_router(market_router)
app.include_router(research_router)
app.include_router(metadata_router)
app.include_router(risk_router)
app.include_router(execution_router)
app.include_router(router)


def create_app() -> FastAPI:
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("marketcore.presentation.dashboard.server:app", host="0.0.0.0", port=8088, reload=False)
