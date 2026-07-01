from __future__ import annotations

from fastapi import FastAPI

from marketcore.presentation.dashboard.api import api_router
from marketcore.presentation.dashboard.router import router
from marketcore.presentation.dashboard.preview_router import preview_router

app = FastAPI(title="Finam_Core Dashboard", version="1.0.0")

app.include_router(api_router)
app.include_router(preview_router)
app.include_router(router)


def create_app() -> FastAPI:
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("marketcore.presentation.dashboard.server:app", host="0.0.0.0", port=8088, reload=False)
