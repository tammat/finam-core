from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class OutcomePartitionKey:
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    run_id: str


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
    """Русский комментарий: FIFO-реконструкция только внутри одного run/strategy/timeframe partition."""

    def __init__(self, max_holding_seconds: float | None = None):
        self.max_holding_seconds = max_holding_seconds
        self.stats = {
            "fills_seen": 0,
            "outcomes_built": 0,
            "partitions_seen": 0,
            "orphan_exit_fills": 0,
            "skipped_excessive_holding": 0,
        }

    def build(self, fills: list[TradeFill]) -> list[TradeOutcome]:
        open_lots: dict[OutcomePartitionKey, list[TradeFill]] = {}
        outcomes: list[TradeOutcome] = []

        for fill in sorted(fills, key=lambda x: (x.ts or datetime.min, x.id)):
            self.stats["fills_seen"] += 1

            side = str(fill.side or "").upper()
            if side not in {"BUY", "SELL"}:
                continue

            remaining = abs(float(fill.qty or 0.0))
            if remaining <= 0:
                continue

            key = self._partition(fill)
            lots = open_lots.setdefault(key, [])

            if not lots or lots[0].side.upper() == side:
                lots.append(self._clone_with_qty(fill, remaining))
                continue

            while remaining > 0 and lots and lots[0].side.upper() != side:
                entry = lots[0]
                matched_qty = min(abs(entry.qty), remaining)

                holding_seconds = self._holding_seconds(entry, fill)
                if (
                    self.max_holding_seconds is not None
                    and holding_seconds is not None
                    and holding_seconds > self.max_holding_seconds
                ):
                    self.stats["skipped_excessive_holding"] += 1
                    lots.pop(0)
                    continue

                outcome = self._build_outcome(entry, fill, matched_qty)
                outcomes.append(outcome)
                self.stats["outcomes_built"] += 1

                entry.qty = abs(entry.qty) - matched_qty
                remaining -= matched_qty

                if abs(entry.qty) <= 1e-12:
                    lots.pop(0)

            if remaining > 0:
                self.stats["orphan_exit_fills"] += 1
                lots.append(self._clone_with_qty(fill, remaining))

        self.stats["partitions_seen"] = len(open_lots)
        return outcomes

    def _build_outcome(self, entry: TradeFill, exit_fill: TradeFill, matched_qty: float) -> TradeOutcome:
        if entry.side.upper() == "BUY" and exit_fill.side.upper() == "SELL":
            gross = (exit_fill.price - entry.price) * matched_qty
        elif entry.side.upper() == "SELL" and exit_fill.side.upper() == "BUY":
            gross = (entry.price - exit_fill.price) * matched_qty
        else:
            gross = 0.0

        commission = self._allocated_commission(entry, exit_fill, matched_qty)
        net = gross - commission

        return TradeOutcome(
            entry_trade_id=entry.id,
            exit_trade_id=exit_fill.id,
            entry_fill_id=entry.fill_id,
            exit_fill_id=exit_fill.fill_id,
            symbol=exit_fill.symbol,
            continuous_symbol=exit_fill.continuous_symbol or entry.continuous_symbol,
            strategy=exit_fill.strategy or entry.strategy,
            timeframe=exit_fill.timeframe or entry.timeframe,
            trade_source=exit_fill.trade_source,
            entry_side=entry.side,
            exit_side=exit_fill.side,
            qty=matched_qty,
            entry_price=entry.price,
            exit_price=exit_fill.price,
            gross_pnl=gross,
            commission=commission,
            net_pnl=net,
            entry_ts=entry.ts,
            exit_ts=exit_fill.ts,
            holding_seconds=self._holding_seconds(entry, exit_fill),
            run_id=self._run_id(exit_fill) or self._run_id(entry),
            raw_json={
                "outcome_engine_version": "trade_outcome_engine_v1_1",
                "partition": self._partition(exit_fill).__dict__,
                "entry_payload": entry.payload,
                "exit_payload": exit_fill.payload,
            },
        )

    def _partition(self, fill: TradeFill) -> OutcomePartitionKey:
        return OutcomePartitionKey(
            symbol=str(fill.symbol or ""),
            strategy=str(fill.strategy or self._payload_value(fill, "strategy") or ""),
            timeframe=str(fill.timeframe or self._payload_value(fill, "timeframe") or ""),
            trade_source=str(fill.trade_source or "paper"),
            run_id=str(self._run_id(fill) or ""),
        )

    @staticmethod
    def _run_id(fill: TradeFill) -> str:
        payload = fill.payload or {}
        return str(
            payload.get("run_id")
            or payload.get("replay_id")
            or payload.get("replay_campaign_id")
            or ""
        )

    @staticmethod
    def _payload_value(fill: TradeFill, key: str) -> Any:
        payload = fill.payload or {}
        nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        return payload.get(key) or nested.get(key)

    @staticmethod
    def _holding_seconds(entry: TradeFill, exit_fill: TradeFill) -> float | None:
        if entry.ts and exit_fill.ts:
            return max((exit_fill.ts - entry.ts).total_seconds(), 0.0)
        return None

    @staticmethod
    def _clone_with_qty(fill: TradeFill, qty: float) -> TradeFill:
        return TradeFill(
            id=fill.id,
            symbol=fill.symbol,
            side=fill.side,
            qty=qty,
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

    @staticmethod
    def _allocated_commission(entry: TradeFill, exit_fill: TradeFill, matched_qty: float) -> float:
        entry_qty = max(abs(entry.qty), matched_qty)
        exit_qty = max(abs(exit_fill.qty), matched_qty)

        entry_part = matched_qty / entry_qty if entry_qty else 0.0
        exit_part = matched_qty / exit_qty if exit_qty else 0.0

        return float(entry.commission or 0.0) * entry_part + float(exit_fill.commission or 0.0) * exit_part
