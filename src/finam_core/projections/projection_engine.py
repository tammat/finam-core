from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from finam_core.events.event_store import StoredEvent


@dataclass
class OrderProjection:
    orders: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class PositionProjection:
    positions: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class PortfolioProjection:
    cash_delta: float = 0.0
    realized_pnl: float = 0.0
    exposure: float = 0.0


@dataclass
class ProjectionState:
    orders: OrderProjection = field(default_factory=OrderProjection)
    positions: PositionProjection = field(default_factory=PositionProjection)
    portfolio: PortfolioProjection = field(default_factory=PortfolioProjection)
    events_processed: int = 0


class ProjectionEngine:
    """Русский комментарий: read-side materialized projections поверх EventStore."""

    FILL_EVENTS = {"FILL", "ORDER_FILLED", "PIPE_FILLED", "PAPER_FILL", "BROKER_FILL"}

    ORDER_STATUS_EVENTS = {
        "ORDER_CREATED",
        "ORDER_DISPATCH_RESULT",
        "OMS_ORDER_CREATED",
        "OMS_ORDER_STATUS_UPDATED",
        "BROKER_ORDER_SYNC_OK",
    }

    def empty_state(self) -> ProjectionState:
        """Русский комментарий: создаёт пустое materialized projection state."""
        return ProjectionState()

    def apply_event(self, state: ProjectionState, event: StoredEvent) -> ProjectionState:
        """Русский комментарий: применяет одно событие к существующему projection state."""
        payload = event.payload or {}
        state.events_processed += 1

        if event.event_type in self.ORDER_STATUS_EVENTS:
            self._apply_order_event(state, event, payload)

        if event.event_type in self.FILL_EVENTS:
            self._apply_fill_event(state, payload)

        self._recalculate_exposure(state)
        return state

    def build(self, events: list[StoredEvent]) -> ProjectionState:
        state = self.empty_state()

        for event in events:
            self.apply_event(state, event)

        return state

    def _apply_order_event(self, state: ProjectionState, event: StoredEvent, payload: dict[str, Any]) -> None:
        order_id = (
            event.aggregate_id
            or payload.get("client_order_id")
            or payload.get("order_id")
            or payload.get("broker_order_id")
        )
        if not order_id:
            return

        current = state.orders.orders.get(str(order_id), {})
        merged = dict(current)
        merged.update({
            "event_type": event.event_type,
            "source": event.source,
            "aggregate_id": event.aggregate_id,
        })

        for key in (
            "client_order_id",
            "broker_order_id",
            "order_id",
            "symbol",
            "side",
            "qty",
            "price",
            "status",
            "reason",
            "oms_status",
        ):
            if key in payload:
                merged[key] = payload.get(key)

        if event.event_type == "ORDER_CREATED" or event.event_type == "OMS_ORDER_CREATED":
            merged.setdefault("status", "CREATED")

        if event.event_type == "ORDER_DISPATCH_RESULT":
            merged["status"] = payload.get("status") or merged.get("status") or "DISPATCHED"

        if event.event_type == "OMS_ORDER_STATUS_UPDATED":
            merged["status"] = payload.get("new_status") or merged.get("status")

        if event.event_type == "BROKER_ORDER_SYNC_OK":
            merged["status"] = payload.get("oms_status") or merged.get("status")

        state.orders.orders[str(order_id)] = merged

    def _apply_fill_event(self, state: ProjectionState, payload: dict[str, Any]) -> None:
        symbol = str(payload.get("symbol") or payload.get("ticker") or "").strip()
        side = str(payload.get("side") or "").upper().strip()
        qty = float(payload.get("qty") or payload.get("quantity") or 0.0)
        price = float(payload.get("price") or payload.get("fill_price") or 0.0)

        if not symbol or side not in {"BUY", "SELL"} or qty <= 0 or price <= 0:
            return

        pos = state.positions.positions.get(
            symbol,
            {
                "qty": 0.0,
                "avg_price": 0.0,
                "realized_pnl": 0.0,
            },
        )

        old_qty = float(pos["qty"])
        old_avg = float(pos["avg_price"])
        realized = float(pos["realized_pnl"])

        signed_qty = qty if side == "BUY" else -qty
        new_qty = old_qty + signed_qty
        avg_price = old_avg

        if side == "BUY":
            state.portfolio.cash_delta -= price * qty

            if old_qty >= 0:
                total_cost = old_avg * old_qty + price * qty
                avg_price = total_cost / new_qty if new_qty else 0.0
            else:
                close_qty = min(abs(old_qty), qty)
                realized += (old_avg - price) * close_qty
                avg_price = old_avg if new_qty != 0 else 0.0

        else:
            state.portfolio.cash_delta += price * qty

            if old_qty <= 0:
                total_cost = old_avg * abs(old_qty) + price * qty
                avg_price = total_cost / abs(new_qty) if new_qty else 0.0
            else:
                close_qty = min(old_qty, qty)
                realized += (price - old_avg) * close_qty
                avg_price = old_avg if new_qty != 0 else 0.0

        state.positions.positions[symbol] = {
            "qty": new_qty,
            "avg_price": avg_price,
            "realized_pnl": realized,
        }

        state.portfolio.realized_pnl = sum(
            float(p["realized_pnl"]) for p in state.positions.positions.values()
        )

    def _recalculate_exposure(self, state: ProjectionState) -> None:
        exposure = 0.0
        for pos in state.positions.positions.values():
            exposure += abs(float(pos["qty"]) * float(pos["avg_price"]))
        state.portfolio.exposure = exposure
