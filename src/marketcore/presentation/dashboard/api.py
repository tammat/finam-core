from __future__ import annotations

from fastapi import APIRouter

from marketcore.presentation.dashboard.services import get_framework_status

api_router = APIRouter()


@api_router.get("/api/framework")
def framework_status() -> dict[str, object]:
    return get_framework_status()
