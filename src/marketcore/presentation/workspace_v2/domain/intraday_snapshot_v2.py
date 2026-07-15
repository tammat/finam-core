from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

@dataclass(frozen=True, slots=True)
class IntradaySnapshotV2:
    session_date: date
    trades_total: int
    instruments_total: int
    pnl: Decimal
    last_trade_at: datetime | None
    paper_status: str
    paper_signals_today: int
    paper_fills_today: int
    paper_pnl_today: Decimal
    paper_refreshed_at: datetime | None
    shadow_orders_total: int
    shadow_fills_total: int
    shadow_positions_total: int
    shadow_last_event_at: datetime | None
    generated_at: datetime
