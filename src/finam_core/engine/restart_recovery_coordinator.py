from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RestartRecoveryResult:
    event: str
    executed: bool
    positions: int
    open_order_symbols: int
    halted_symbols: int
    error: str | None = None


class RestartRecoveryCoordinator:
    """Русский комментарий: orchestration-layer для restart recovery."""

    def __init__(self, pipeline: Any) -> None:
        self.pipeline = pipeline

    def run_if_needed(self) -> RestartRecoveryResult:
        if getattr(self.pipeline, "_restart_recovery_done", False):
            return RestartRecoveryResult(
                event="RESTART_RECOVERY_SKIPPED",
                executed=False,
                positions=0,
                open_order_symbols=0,
                halted_symbols=0,
                error=None,
            )

        if os.getenv("ENABLE_RESTART_RECOVERY", "0") != "1":
            self.pipeline._restart_recovery_done = True
            return RestartRecoveryResult(
                event="RESTART_RECOVERY_DISABLED",
                executed=False,
                positions=0,
                open_order_symbols=0,
                halted_symbols=0,
                error=None,
            )

        try:
            print("PIPE_RESTART_RECOVERY_START", flush=True)

            self.pipeline._sync_broker_positions_readonly()
            self.pipeline._sync_broker_open_orders_if_needed()

            broker_positions = getattr(self.pipeline, "_broker_position_qty_by_symbol", {}) or {}
            broker_orders = getattr(self.pipeline, "_broker_orders_by_symbol", {}) or {}

            if hasattr(self.pipeline, "engine_coordinator"):
                from finam_core.engine.coordinator_flags import CoordinatorFlags

                if CoordinatorFlags.reconcile_enabled():
                    result = self.pipeline.engine_coordinator.reconcile(
                        broker_positions=[
                            {"symbol": symbol, "qty": qty}
                            for symbol, qty in broker_positions.items()
                        ],
                        broker_orders=[
                            {"symbol": symbol, "orders": orders}
                            for symbol, orders in broker_orders.items()
                        ],
                        context={"source": "restart_recovery"},
                    )
                    print(
                        f"PIPE_ENGINE_COORDINATOR_RECONCILE "
                        f"processed={getattr(result, 'reconciliation_processed', False)} "
                        f"errors={getattr(result, 'errors', [])}",
                        flush=True,
                    )

            self.pipeline._refresh_broker_position_hard_gate()

            broker_positions = getattr(self.pipeline, "_broker_position_qty_by_symbol", {}) or {}
            broker_orders = getattr(self.pipeline, "_broker_orders_by_symbol", {}) or {}
            halted = getattr(self.pipeline, "_broker_position_halt_by_symbol", {}) or {}

            print(
                f"PIPE_RESTART_RECOVERY_DONE positions={len(broker_positions)} "
                f"open_order_symbols={len(broker_orders)} halted_symbols={len(halted)}",
                flush=True,
            )
            self.pipeline._restart_recovery_done = True

            return RestartRecoveryResult(
                event="RESTART_RECOVERY_DONE",
                executed=True,
                positions=len(broker_positions),
                open_order_symbols=len(broker_orders),
                halted_symbols=len(halted),
                error=None,
            )

        except Exception as exc:
            print(f"PIPE_RESTART_RECOVERY_ERROR error={exc}", flush=True)
            self.pipeline._restart_recovery_done = True
            return RestartRecoveryResult(
                event="RESTART_RECOVERY_ERROR",
                executed=False,
                positions=0,
                open_order_symbols=0,
                halted_symbols=0,
                error=str(exc),
            )
