from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionGatewayInput:
    """Русский комментарий: DTO для маршрутизации intent в execution layer."""
    intent: dict[str, Any]
    state: dict[str, Any]
    source: str = "pipeline"


class ExecutionGateway:
    """
    Русский комментарий:
    Execution Routing Layer.

    Этап 1:
    thin-wrapper над текущими методами PaperTradingPipeline.
    Поведение не меняем.
    """

    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline

    def apply_execution_decision(self, data: ExecutionGatewayInput) -> dict[str, Any]:
        p = self.pipeline
        return p._apply_execution_decision_if_enabled(data.intent, data.state)

    def route_order_if_enabled(self, data: ExecutionGatewayInput) -> dict[str, Any]:
        p = self.pipeline

        if hasattr(p, "_route_order_if_enabled"):
            return p._route_order_if_enabled(data.intent, data.state)

        return data.intent
