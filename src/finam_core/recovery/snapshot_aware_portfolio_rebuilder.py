from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from finam_core.events.event_store_reader import EventStoreReader
from finam_core.recovery.portfolio_rebuilder import (
    PortfolioRebuilder,
    PortfolioRebuildResult,
    RebuiltPosition,
)
from finam_core.recovery.recovery_snapshot_service import RecoverySnapshotService


@dataclass(frozen=True)
class SnapshotAwareRebuildResult:
    positions: dict[str, RebuiltPosition] = field(default_factory=dict)
    cash_delta: float = 0.0
    realized_pnl: float = 0.0
    base_event_offset: int = 0
    delta_events_processed: int = 0
    used_snapshot: bool = False


class SnapshotAwarePortfolioRebuilder:
    """Русский комментарий: восстановление portfolio через latest snapshot + delta events."""

    def __init__(
        self,
        *,
        reader: EventStoreReader | None = None,
        snapshots: RecoverySnapshotService | None = None,
        rebuilder: PortfolioRebuilder | None = None,
    ) -> None:
        self.reader = reader or EventStoreReader()
        self.snapshots = snapshots or RecoverySnapshotService()
        self.rebuilder = rebuilder or PortfolioRebuilder(reader=self.reader)

    @staticmethod
    def _positions_from_snapshot(raw: dict[str, Any]) -> dict[str, RebuiltPosition]:
        result: dict[str, RebuiltPosition] = {}

        for symbol, item in (raw or {}).items():
            result[str(symbol)] = RebuiltPosition(
                symbol=str(item.get("symbol") or symbol),
                qty=float(item.get("qty") or 0.0),
                avg_price=float(item.get("avg_price") or 0.0),
                realized_pnl=float(item.get("realized_pnl") or 0.0),
            )

        return result

    @staticmethod
    def _apply_fill(
        *,
        positions: dict[str, RebuiltPosition],
        symbol: str,
        side: str,
        qty: float,
        price: float,
    ) -> None:
        """Русский комментарий: применяет один fill поверх snapshot state с расчётом realized PnL."""
        prev = positions.get(
            symbol,
            RebuiltPosition(symbol=symbol, qty=0.0, avg_price=0.0, realized_pnl=0.0),
        )

        signed_qty = qty if side == "BUY" else -qty
        new_qty = float(prev.qty) + signed_qty
        realized_pnl = float(prev.realized_pnl)
        avg_price = float(prev.avg_price)

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

        positions[symbol] = RebuiltPosition(
            symbol=symbol,
            qty=new_qty,
            avg_price=avg_price,
            realized_pnl=realized_pnl,
        )

    def _apply_delta_events(
        self,
        *,
        base_positions: dict[str, RebuiltPosition],
        base_cash_delta: float,
        delta_events,
    ) -> tuple[dict[str, RebuiltPosition], float, float, int]:
        """Русский комментарий: применяет delta fill events поверх snapshot, а не rebuild с нуля."""
        positions = dict(base_positions)
        cash_delta = float(base_cash_delta)
        processed = 0

        for event in delta_events:
            if event.event_type not in PortfolioRebuilder.FILL_EVENT_TYPES:
                continue

            payload = event.payload or {}

            symbol = str(payload.get("symbol") or payload.get("ticker") or "").strip()
            side = str(payload.get("side") or "").upper().strip()
            qty = float(payload.get("qty") or payload.get("quantity") or 0.0)
            price = float(payload.get("price") or payload.get("fill_price") or 0.0)

            if not symbol or side not in {"BUY", "SELL"} or qty <= 0 or price <= 0:
                continue

            self._apply_fill(
                positions=positions,
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
            )

            cash_delta += -price * qty if side == "BUY" else price * qty
            processed += 1

        realized_pnl = sum(float(p.realized_pnl) for p in positions.values())
        return positions, cash_delta, realized_pnl, processed

    def rebuild(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
    ) -> SnapshotAwareRebuildResult:
        snapshot = self.snapshots.latest_snapshot(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
        )

        if snapshot is None:
            full = self.rebuilder.rebuild_aggregate(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
            )
            realized_pnl = sum(float(p.realized_pnl) for p in full.positions.values())

            return SnapshotAwareRebuildResult(
                positions=full.positions,
                cash_delta=full.cash_delta,
                realized_pnl=realized_pnl,
                base_event_offset=0,
                delta_events_processed=full.events_processed,
                used_snapshot=False,
            )

        base_positions = self._positions_from_snapshot(snapshot.positions)

        delta_events = [
            event
            for event in self.reader.list_since_id(
                since_id=int(snapshot.event_offset),
                limit=100000,
            )
            if event.aggregate_type == aggregate_type and event.aggregate_id == aggregate_id
        ]

        positions, cash_delta, realized_pnl, delta_processed = self._apply_delta_events(
            base_positions=base_positions,
            base_cash_delta=float(snapshot.cash_delta),
            delta_events=delta_events,
        )

        return SnapshotAwareRebuildResult(
            positions=positions,
            cash_delta=cash_delta,
            realized_pnl=realized_pnl,
            base_event_offset=int(snapshot.event_offset),
            delta_events_processed=delta_processed,
            used_snapshot=True,
        )
