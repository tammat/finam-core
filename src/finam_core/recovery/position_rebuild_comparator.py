from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from finam_core.recovery.portfolio_rebuilder import PortfolioRebuilder
from finam_core.risk.persistent_kill_switch import PersistentKillSwitch


@dataclass(frozen=True)
class PositionRebuildMismatch:
    symbol: str
    rebuilt_qty: float
    broker_qty: float
    local_qty: float
    kind: str


@dataclass(frozen=True)
class PositionRebuildCompareResult:
    ok: bool
    reason: str
    mismatches: list[PositionRebuildMismatch] = field(default_factory=list)


class PositionRebuildComparator:
    """Русский комментарий: сравнивает EventStore rebuild с broker/local позициями."""

    def __init__(
        self,
        *,
        portfolio_rebuilder: PortfolioRebuilder,
        positions_client: Any,
        managed_service: Any,
        kill_switch: PersistentKillSwitch | None = None,
        qty_tolerance: float = 0.000001,
        activate_kill_switch_on_mismatch: bool = True,
    ) -> None:
        self.portfolio_rebuilder = portfolio_rebuilder
        self.positions_client = positions_client
        self.managed_service = managed_service
        self.kill_switch = kill_switch
        self.qty_tolerance = float(qty_tolerance)
        self.activate_kill_switch_on_mismatch = bool(activate_kill_switch_on_mismatch)

    def _load_broker_positions(self) -> dict[str, float]:
        if hasattr(self.positions_client, "get_positions"):
            positions = self.positions_client.get_positions()
        elif hasattr(self.positions_client, "list_positions"):
            positions = self.positions_client.list_positions()
        else:
            return {}

        result: dict[str, float] = {}
        for p in positions or []:
            if isinstance(p, dict):
                symbol = str(p.get("symbol") or p.get("ticker") or "")
                qty = float(p.get("qty") or p.get("quantity") or 0.0)
            else:
                symbol = str(getattr(p, "symbol", None) or getattr(p, "ticker", None) or "")
                qty = float(getattr(p, "qty", None) or getattr(p, "quantity", None) or 0.0)

            if symbol:
                result[symbol] = qty

        return result

    def _load_local_positions(self) -> dict[str, float]:
        repo = getattr(self.managed_service, "repository", None)
        if repo is None or not hasattr(repo, "list_all"):
            return {}

        result: dict[str, float] = {}
        for p in repo.list_all() or []:
            if isinstance(p, dict):
                symbol = str(p.get("symbol") or p.get("ticker") or "")
                qty = float(p.get("qty") or p.get("quantity") or 0.0)
            else:
                symbol = str(getattr(p, "symbol", None) or getattr(p, "ticker", None) or "")
                qty = float(getattr(p, "qty", None) or getattr(p, "quantity", None) or 0.0)

            if symbol:
                result[symbol] = qty

        return result

    def compare_aggregate(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
    ) -> PositionRebuildCompareResult:
        rebuild = self.portfolio_rebuilder.rebuild_aggregate(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
        )

        rebuilt_positions = {
            symbol: float(pos.qty)
            for symbol, pos in rebuild.positions.items()
        }
        broker_positions = self._load_broker_positions()
        local_positions = self._load_local_positions()

        symbols = set(rebuilt_positions) | set(broker_positions) | set(local_positions)
        mismatches: list[PositionRebuildMismatch] = []

        for symbol in sorted(symbols):
            rebuilt_qty = float(rebuilt_positions.get(symbol, 0.0))
            broker_qty = float(broker_positions.get(symbol, 0.0))
            local_qty = float(local_positions.get(symbol, 0.0))

            rebuilt_vs_broker = abs(rebuilt_qty - broker_qty) > self.qty_tolerance
            rebuilt_vs_local = abs(rebuilt_qty - local_qty) > self.qty_tolerance
            broker_vs_local = abs(broker_qty - local_qty) > self.qty_tolerance

            if not (rebuilt_vs_broker or rebuilt_vs_local or broker_vs_local):
                continue

            if broker_vs_local:
                kind = "broker_local_qty_mismatch"
            elif rebuilt_vs_broker:
                kind = "rebuilt_broker_qty_mismatch"
            else:
                kind = "rebuilt_local_qty_mismatch"

            mismatches.append(
                PositionRebuildMismatch(
                    symbol=symbol,
                    rebuilt_qty=rebuilt_qty,
                    broker_qty=broker_qty,
                    local_qty=local_qty,
                    kind=kind,
                )
            )

        if mismatches:
            if self.activate_kill_switch_on_mismatch:
                ks = self.kill_switch or PersistentKillSwitch()
                ks.activate(
                    scope="GLOBAL",
                    reason="portfolio_rebuild_mismatch",
                    source="position_rebuild_comparator",
                )

            return PositionRebuildCompareResult(
                ok=False,
                reason="portfolio_rebuild_mismatch",
                mismatches=mismatches,
            )

        return PositionRebuildCompareResult(
            ok=True,
            reason="portfolio_rebuild_ok",
            mismatches=[],
        )
