from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.risk.context_builders import build_risk_context


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
        self.last_context = None

    def route(self, data: RiskRouteInput):
        p = self.pipeline

        ctx = build_risk_context(data.intent, p.portfolio, data.state)
        self.last_context = ctx

        print(
            f"{data.label}_CTX symbol={ctx.symbol} qty={ctx.qty} price={ctx.price} "
            f"value={ctx.trade_value} exposure={ctx.total_exposure}",
            flush=True,
        )

        return p.risk.evaluate(signal=data.intent, context=ctx)
