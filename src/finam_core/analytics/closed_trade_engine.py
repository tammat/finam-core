# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Any


@dataclass(frozen=True)
class TradeFill:
    id: int
    ts: str
    symbol: str
    side: str
    qty: float
    price: float
    commission: float = 0.0
    fill_id: str | None = None
    payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class ClosedTrade:
    symbol: str
    side: str
    entry_ts: str
    exit_ts: str
    qty: float
    entry_price: float
    exit_price: float
    gross_pnl: float
    commission: float
    net_pnl: float
    signal_id: str | None = None
    strategy: str | None = None
    horizon: str | None = None
    regime: str | None = None
    payload: dict[str, Any] | None = None


class ClosedTradeEngine:
    """
    FIFO pairing engine.

    BUY -> SELL закрывает long.
    SELL -> BUY закрывает short.

    Пока считаем простую модель без плеча и мультипликатора.
    Для фьючерсов позже добавим contract_multiplier.
    """

    def build_closed_trades(self, fills: Iterable[TradeFill]) -> list[ClosedTrade]:
        positions: dict[str, list[TradeFill]] = {}
        closed: list[ClosedTrade] = []

        for fill in fills:
            symbol = fill.symbol
            side = fill.side.upper()
            qty_left = float(fill.qty)

            queue = positions.setdefault(symbol, [])

            opposite_side = "SELL" if side == "BUY" else "BUY"

            while qty_left > 0 and queue and queue[0].side.upper() == opposite_side:
                open_fill = queue[0]

                matched_qty = min(qty_left, open_fill.qty)

                closed.append(
                    self._close_pair(
                        open_fill=open_fill,
                        close_fill=fill,
                        matched_qty=matched_qty,
                    )
                )

                qty_left -= matched_qty

                remaining_open_qty = open_fill.qty - matched_qty

                if remaining_open_qty <= 0:
                    queue.pop(0)
                else:
                    queue[0] = TradeFill(
                        id=open_fill.id,
                        ts=open_fill.ts,
                        symbol=open_fill.symbol,
                        side=open_fill.side,
                        qty=remaining_open_qty,
                        price=open_fill.price,
                        commission=open_fill.commission,
                        fill_id=open_fill.fill_id,
                        payload=open_fill.payload,
                    )

            if qty_left > 0:
                queue.append(
                    TradeFill(
                        id=fill.id,
                        ts=fill.ts,
                        symbol=fill.symbol,
                        side=fill.side,
                        qty=qty_left,
                        price=fill.price,
                        commission=fill.commission,
                        fill_id=fill.fill_id,
                        payload=fill.payload,
                    )
                )

        return closed

    def _close_pair(
        self,
        *,
        open_fill: TradeFill,
        close_fill: TradeFill,
        matched_qty: float,
    ) -> ClosedTrade:
        open_side = open_fill.side.upper()

        if open_side == "BUY":
            trade_side = "LONG"
            gross_pnl = (close_fill.price - open_fill.price) * matched_qty
        else:
            trade_side = "SHORT"
            gross_pnl = (open_fill.price - close_fill.price) * matched_qty

        commission = self._proportional_commission(open_fill, matched_qty) + self._proportional_commission(close_fill, matched_qty)
        net_pnl = gross_pnl - commission

        entry_payload = open_fill.payload or {}
        exit_payload = close_fill.payload or {}

        signal_id = (
            entry_payload.get("signal_id")
            or exit_payload.get("signal_id")
        )
        strategy = (
            entry_payload.get("strategy")
            or exit_payload.get("strategy")
        )
        horizon = (
            entry_payload.get("horizon")
            or entry_payload.get("signal_horizon")
            or exit_payload.get("horizon")
            or exit_payload.get("signal_horizon")
        )
        regime = (
            entry_payload.get("regime")
            or exit_payload.get("regime")
        )

        payload = {
            "entry_fill_id": open_fill.fill_id,
            "exit_fill_id": close_fill.fill_id,
            "entry_payload": entry_payload,
            "exit_payload": exit_payload,

            # Русский комментарий:
            # replay metadata поднимаем в top-level payload,
            # чтобы analytics/reporting могли фильтровать кампании SQL-запросом.
            "replay_campaign_id": (
                entry_payload.get("replay_campaign_id")
                or exit_payload.get("replay_campaign_id")
            ),
            "replay_id": (
                entry_payload.get("replay_id")
                or exit_payload.get("replay_id")
            ),
            "replay_symbol": (
                entry_payload.get("replay_symbol")
                or exit_payload.get("replay_symbol")
            ),
            "replay_timeframe": (
                entry_payload.get("replay_timeframe")
                or exit_payload.get("replay_timeframe")
            ),
            "replay_strategy": (
                entry_payload.get("replay_strategy")
                or exit_payload.get("replay_strategy")
            ),
            "dataset_source": (
                entry_payload.get("dataset_source")
                or exit_payload.get("dataset_source")
            ),
        }

        return ClosedTrade(
            symbol=open_fill.symbol,
            side=trade_side,
            entry_ts=open_fill.ts,
            exit_ts=close_fill.ts,
            qty=matched_qty,
            entry_price=open_fill.price,
            exit_price=close_fill.price,
            gross_pnl=gross_pnl,
            commission=commission,
            net_pnl=net_pnl,
            signal_id=signal_id,
            strategy=strategy,
            horizon=horizon,
            regime=regime,
            payload=payload,
        )

    @staticmethod
    def _proportional_commission(fill: TradeFill, matched_qty: float) -> float:
        if fill.qty <= 0:
            return 0.0
        return float(fill.commission or 0.0) * matched_qty / fill.qty


def summarize_closed_trades(closed: list[ClosedTrade]) -> dict:
    total = len(closed)

    if total == 0:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
        }

    wins = [t for t in closed if t.net_pnl > 0]
    losses = [t for t in closed if t.net_pnl < 0]

    gross_profit = sum(t.net_pnl for t in wins)
    gross_loss = abs(sum(t.net_pnl for t in losses))

    net_pnl = sum(t.net_pnl for t in closed)

    return {
        "trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "winrate": len(wins) / total * 100.0,
        "gross_pnl": sum(t.gross_pnl for t in closed),
        "net_pnl": net_pnl,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else 0.0,
        "expectancy": net_pnl / total,
    }
