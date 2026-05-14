from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TradingEngineCoordinatorResult:
    event: str
    quote_processed: bool
    reconciliation_processed: bool
    execution_processed: bool
    errors: list[str]


class TradingEngineCoordinator:
    """
    Русский комментарий:
    Верхнеуровневый orchestration-layer торгового движка.

    Задача:
    - координировать PipelineKernel, ExecutionGateway и PortfolioReconciliationLayer;
    - не считать PnL;
    - не проводить fill accounting;
    - не принимать risk decision самостоятельно;
    - не отправлять заявки напрямую.
    """

    def __init__(
        self,
        pipeline_kernel: Any | None = None,
        execution_gateway: Any | None = None,
        portfolio_reconciliation_layer: Any | None = None,
    ):
        self.pipeline_kernel = pipeline_kernel
        self.execution_gateway = execution_gateway
        self.portfolio_reconciliation_layer = portfolio_reconciliation_layer

    def on_quote(self, event: Any) -> TradingEngineCoordinatorResult:
        errors: list[str] = []
        quote_processed = False
        execution_processed = False

        if self.pipeline_kernel is not None:
            try:
                process_quote = getattr(self.pipeline_kernel, "process_quote", None)
                if callable(process_quote):
                    process_quote(event)
                else:
                    run = getattr(self.pipeline_kernel, "run", None)
                    if callable(run):
                        run(event)
                quote_processed = True
            except Exception as exc:
                errors.append(f"quote_processing_failed:{exc}")

        return TradingEngineCoordinatorResult(
            event="TRADING_ENGINE_COORDINATOR_QUOTE_RESULT",
            quote_processed=quote_processed,
            reconciliation_processed=False,
            execution_processed=execution_processed,
            errors=errors,
        )

    def route_execution(self, intent: dict[str, Any], market_state: dict[str, Any]) -> Any:
        if self.execution_gateway is None:
            return intent

        route = getattr(self.execution_gateway, "route", None)
        if callable(route):
            return route(intent=intent, state=market_state)

        dispatch = getattr(self.execution_gateway, "dispatch", None)
        if callable(dispatch):
            return dispatch(intent=intent, state=market_state)

        return intent

    def reconcile(
        self,
        broker_positions: list[Any] | None = None,
        broker_orders: list[Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> TradingEngineCoordinatorResult:
        errors: list[str] = []
        reconciliation_processed = False

        if self.portfolio_reconciliation_layer is not None:
            try:
                self.portfolio_reconciliation_layer.run(
                    broker_positions=broker_positions or [],
                    broker_orders=broker_orders or [],
                    context=context or {},
                )
                reconciliation_processed = True
            except Exception as exc:
                errors.append(f"reconciliation_failed:{exc}")

        return TradingEngineCoordinatorResult(
            event="TRADING_ENGINE_COORDINATOR_RECONCILIATION_RESULT",
            quote_processed=False,
            reconciliation_processed=reconciliation_processed,
            execution_processed=False,
            errors=errors,
        )
