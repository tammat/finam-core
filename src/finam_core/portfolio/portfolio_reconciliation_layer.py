from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PortfolioReconciliationResult:
    event: str
    positions_synced: int
    open_orders_synced: bool
    repair_checked: bool
    errors: list[str]


class PortfolioReconciliationLayer:
    """
    Русский комментарий:
    Единый orchestration-layer для сверки портфеля.

    Важно:
    - не проводит сделки;
    - не меняет cash;
    - не считает PnL;
    - не заменяет PositionManager;
    - только координирует broker/local reconciliation.
    """

    def __init__(
        self,
        position_sync_layer: Any | None = None,
        open_orders_sync: Any | None = None,
        reconciliation_repair: Any | None = None,
    ):
        self.position_sync_layer = position_sync_layer
        self.open_orders_sync = open_orders_sync
        self.reconciliation_repair = reconciliation_repair

    def run(
        self,
        broker_positions: list[Any] | None = None,
        broker_orders: list[Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> PortfolioReconciliationResult:
        errors: list[str] = []
        positions_synced = 0
        open_orders_synced = False
        repair_checked = False

        broker_positions = broker_positions or []
        broker_orders = broker_orders or []
        context = context or {}

        if self.position_sync_layer is not None:
            for position in broker_positions:
                try:
                    self.position_sync_layer.sync_position(position)
                    positions_synced += 1
                except Exception as exc:
                    errors.append(f"position_sync_failed:{exc}")

        if self.open_orders_sync is not None:
            try:
                sync = getattr(self.open_orders_sync, "sync", None)
                if callable(sync):
                    sync(broker_orders=broker_orders, context=context)
                open_orders_synced = True
            except TypeError:
                try:
                    self.open_orders_sync.sync()
                    open_orders_synced = True
                except Exception as exc:
                    errors.append(f"open_orders_sync_failed:{exc}")
            except Exception as exc:
                errors.append(f"open_orders_sync_failed:{exc}")

        if self.reconciliation_repair is not None:
            try:
                check = (
                    getattr(self.reconciliation_repair, "run", None)
                    or getattr(self.reconciliation_repair, "check", None)
                    or getattr(self.reconciliation_repair, "repair", None)
                )
                if callable(check):
                    check(context=context)
                repair_checked = True
            except TypeError:
                try:
                    check()
                    repair_checked = True
                except Exception as exc:
                    errors.append(f"repair_check_failed:{exc}")
            except Exception as exc:
                errors.append(f"repair_check_failed:{exc}")

        return PortfolioReconciliationResult(
            event="PORTFOLIO_RECONCILIATION_LAYER_RESULT",
            positions_synced=positions_synced,
            open_orders_synced=open_orders_synced,
            repair_checked=repair_checked,
            errors=errors,
        )
