from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from finam_core.events.event_store_reader import EventStoreReader


@dataclass(frozen=True)
class RebuiltPosition:
    symbol: str
    qty: float
    avg_price: float
    realized_pnl: float = 0.0


@dataclass(frozen=True)
class PortfolioRebuildResult:
    positions: dict[str, RebuiltPosition] = field(default_factory=dict)
    cash_delta: float = 0.0
    events_processed: int = 0


class PortfolioRebuilder:
    """Русский комментарий: read-only восстановление portfolio state из EventStore."""

    FILL_EVENT_TYPES = {
        "FILL",
        "ORDER_FILLED",
        "PIPE_FILLED",
        "PAPER_FILL",
        "BROKER_FILL",
    }

    def __init__(self, reader: EventStoreReader | None = None) -> None:
        self.reader = reader or EventStoreReader()

    @staticmethod
    def _payload_value(payload: dict[str, Any], *names: str, default=None):
        for name in names:
            if name in payload:
                return payload.get(name)
        return default

    def rebuild_from_events(self, events) -> PortfolioRebuildResult:
        positions: dict[str, RebuiltPosition] = {}
        cash_delta = 0.0
        processed = 0

        for event in events:
            if event.event_type not in self.FILL_EVENT_TYPES:
                continue

            payload = event.payload or {}

            symbol = str(self._payload_value(payload, "symbol", "ticker", default="")).strip()
            side = str(self._payload_value(payload, "side", default="")).upper().strip()
            qty = float(self._payload_value(payload, "qty", "quantity", default=0.0) or 0.0)
            price = float(self._payload_value(payload, "price", "fill_price", default=0.0) or 0.0)

            if not symbol or side not in {"BUY", "SELL"} or qty <= 0 or price <= 0:
                continue

            processed += 1

            prev = positions.get(
                symbol,
                RebuiltPosition(symbol=symbol, qty=0.0, avg_price=0.0, realized_pnl=0.0),
            )

            signed_qty = qty if side == "BUY" else -qty
            new_qty = prev.qty + signed_qty

            realized_pnl = prev.realized_pnl
            avg_price = prev.avg_price

            if side == "BUY":
                if prev.qty >= 0:
                    total_cost = prev.avg_price * prev.qty + price * qty
                    avg_price = total_cost / new_qty if new_qty else 0.0
                else:
                    close_qty = min(abs(prev.qty), qty)
                    realized_pnl += (prev.avg_price - price) * close_qty
                    avg_price = prev.avg_price if new_qty != 0 else 0.0
            else:
                if prev.qty <= 0:
                    total_cost = prev.avg_price * abs(prev.qty) + price * qty
                    avg_price = total_cost / abs(new_qty) if new_qty else 0.0
                else:
                    close_qty = min(prev.qty, qty)
                    realized_pnl += (price - prev.avg_price) * close_qty
                    avg_price = prev.avg_price if new_qty != 0 else 0.0

            cash_delta += -price * qty if side == "BUY" else price * qty

            positions[symbol] = RebuiltPosition(
                symbol=symbol,
                qty=new_qty,
                avg_price=avg_price,
                realized_pnl=realized_pnl,
            )

        return PortfolioRebuildResult(
            positions=positions,
            cash_delta=cash_delta,
            events_processed=processed,
        )

    def rebuild_aggregate(self, *, aggregate_type: str, aggregate_id: str) -> PortfolioRebuildResult:
        replay = self.reader.replay_aggregate(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
        )
        return self.rebuild_from_events(replay.events)
