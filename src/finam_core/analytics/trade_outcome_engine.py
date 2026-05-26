from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TradeFill:
    id: int
    symbol: str
    side: str
    qty: float
    price: float
    commission: float
    ts: datetime | None
    fill_id: str | None
    trade_source: str
    strategy: str | None
    timeframe: str | None
    continuous_symbol: str | None
    payload: dict[str, Any]


@dataclass
class TradeOutcome:
    entry_trade_id: int
    exit_trade_id: int
    entry_fill_id: str | None
    exit_fill_id: str | None
    symbol: str
    continuous_symbol: str | None
    strategy: str | None
    timeframe: str | None
    trade_source: str
    entry_side: str
    exit_side: str
    qty: float
    entry_price: float
    exit_price: float
    gross_pnl: float
    commission: float
    net_pnl: float
    entry_ts: datetime | None
    exit_ts: datetime | None
    holding_seconds: float | None
    run_id: str | None
    raw_json: dict[str, Any]


class TradeOutcomeEngine:
    """Русский комментарий: FIFO-реконструкция закрытых сделок по fills без влияния на execution."""

    def build(self, fills: list[TradeFill]) -> list[TradeOutcome]:
        open_lots: list[TradeFill] = []
        outcomes: list[TradeOutcome] = []

        for fill in sorted(fills, key=lambda x: (x.ts or datetime.min, x.id)):
            side = fill.side.upper()
            if side not in {"BUY", "SELL"}:
                continue

            remaining = abs(float(fill.qty or 0.0))
            if remaining <= 0:
                continue

            while remaining > 0 and open_lots and open_lots[0].side.upper() != side:
                entry = open_lots[0]
                matched_qty = min(abs(entry.qty), remaining)

                if entry.side.upper() == "BUY" and side == "SELL":
                    gross = (fill.price - entry.price) * matched_qty
                elif entry.side.upper() == "SELL" and side == "BUY":
                    gross = (entry.price - fill.price) * matched_qty
                else:
                    gross = 0.0

                commission = self._allocated_commission(entry, fill, matched_qty)
                net = gross - commission

                holding_seconds = None
                if entry.ts and fill.ts:
                    holding_seconds = max((fill.ts - entry.ts).total_seconds(), 0.0)

                outcomes.append(
                    TradeOutcome(
                        entry_trade_id=entry.id,
                        exit_trade_id=fill.id,
                        entry_fill_id=entry.fill_id,
                        exit_fill_id=fill.fill_id,
                        symbol=fill.symbol,
                        continuous_symbol=fill.continuous_symbol or entry.continuous_symbol,
                        strategy=fill.strategy or entry.strategy,
                        timeframe=fill.timeframe or entry.timeframe,
                        trade_source=fill.trade_source,
                        entry_side=entry.side,
                        exit_side=fill.side,
                        qty=matched_qty,
                        entry_price=entry.price,
                        exit_price=fill.price,
                        gross_pnl=gross,
                        commission=commission,
                        net_pnl=net,
                        entry_ts=entry.ts,
                        exit_ts=fill.ts,
                        holding_seconds=holding_seconds,
                        run_id=str(fill.payload.get("run_id") or entry.payload.get("run_id") or ""),
                        raw_json={
                            "entry_payload": entry.payload,
                            "exit_payload": fill.payload,
                        },
                    )
                )

                entry.qty = abs(entry.qty) - matched_qty
                remaining -= matched_qty

                if abs(entry.qty) <= 1e-12:
                    open_lots.pop(0)

            if remaining > 0:
                open_lots.append(
                    TradeFill(
                        id=fill.id,
                        symbol=fill.symbol,
                        side=fill.side,
                        qty=remaining,
                        price=fill.price,
                        commission=fill.commission,
                        ts=fill.ts,
                        fill_id=fill.fill_id,
                        trade_source=fill.trade_source,
                        strategy=fill.strategy,
                        timeframe=fill.timeframe,
                        continuous_symbol=fill.continuous_symbol,
                        payload=fill.payload,
                    )
                )

        return outcomes

    @staticmethod
    def _allocated_commission(entry: TradeFill, exit_fill: TradeFill, matched_qty: float) -> float:
        # Русский комментарий: минимальная v1-модель комиссий; дальше заменим на точное распределение по partial fills.
        entry_qty = max(abs(entry.qty), matched_qty)
        exit_qty = max(abs(exit_fill.qty), matched_qty)

        entry_part = matched_qty / entry_qty if entry_qty else 0.0
        exit_part = matched_qty / exit_qty if exit_qty else 0.0

        return float(entry.commission or 0.0) * entry_part + float(exit_fill.commission or 0.0) * exit_part
