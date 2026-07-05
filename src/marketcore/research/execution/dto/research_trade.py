from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4


TradeSide = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class ResearchTrade:
    trade_uuid: UUID
    signal_uuid: UUID | None
    entry_ts: datetime
    exit_ts: datetime
    side: TradeSide
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    commission: float
    slippage: float
    net_pnl: float
    execution_model: str
    metadata: dict

    @staticmethod
    def create(
        signal_uuid: UUID | None,
        entry_ts: datetime,
        exit_ts: datetime,
        side: TradeSide,
        entry_price: float,
        exit_price: float,
        quantity: float,
        commission: float,
        slippage: float,
        execution_model: str,
        metadata: dict | None = None,
    ) -> "ResearchTrade":
        signed_qty = quantity if side == "BUY" else -quantity
        gross_pnl = (exit_price - entry_price) * signed_qty
        net_pnl = gross_pnl - commission - slippage

        return ResearchTrade(
            trade_uuid=uuid4(),
            signal_uuid=signal_uuid,
            entry_ts=entry_ts,
            exit_ts=exit_ts,
            side=side,
            entry_price=float(entry_price),
            exit_price=float(exit_price),
            quantity=float(quantity),
            gross_pnl=float(gross_pnl),
            commission=float(commission),
            slippage=float(slippage),
            net_pnl=float(net_pnl),
            execution_model=execution_model,
            metadata=metadata or {},
        )
