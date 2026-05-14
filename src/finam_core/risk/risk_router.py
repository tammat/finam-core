from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RiskRouteInput:
    symbol: str
    intent: dict[str, Any]
    state: dict[str, Any]
    label: str = "PIPE_RISK"


class RiskRouter:
    """Русский комментарий: единый слой маршрутизации intent через RiskEngine."""

    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline

    def route(self, data: RiskRouteInput):
        p = self.pipeline

        # Русский комментарий:
        # build_risk_context пока берём из пространства paper_pipeline,
        # чтобы не завязаться на неверный модуль при refactor.
        import finam_core.pipelines.paper_pipeline as paper_pipeline

        ctx = paper_pipeline.build_risk_context(data.intent, p.portfolio, data.state)

        print(
            f"{data.label}_CTX symbol={ctx.symbol} qty={ctx.qty} price={ctx.price} "
            f"value={ctx.trade_value} exposure={ctx.total_exposure}",
            flush=True,
        )

        return p.risk.evaluate(signal=data.intent, context=ctx)
