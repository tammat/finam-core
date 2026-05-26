from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class TradeContextSnapshot:
    trade_id: str
    symbol: str
    strategy: str
    timeframe: str
    event_type: str = "paper_trade"
    continuous_symbol: str | None = None
    db_trade_id: int | None = None
    run_id: str | None = None
    side: str | None = None
    qty: float | None = None
    price: float | None = None
    reason: str | None = None
    source: str | None = None
    ts: datetime | None = None
    snapshot: dict[str, Any] | None = None


class TradeContextSnapshotRepository:
    """Русский комментарий: сохраняет explainability snapshot сделки без влияния на execution."""

    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("database_url is required")
        self.database_url = database_url

    def save(self, item: TradeContextSnapshot) -> None:
        if not item.trade_id:
            raise ValueError("trade_id is required")

        sql = """
        INSERT INTO trade_context_snapshots (
            trade_id, db_trade_id, run_id,
            symbol, continuous_symbol, strategy, timeframe, trade_source,
            side, qty, price,
            reason, source, event_type, ts,
            snapshot
        )
        VALUES (
            %(trade_id)s, %(db_trade_id)s, %(run_id)s,
            %(symbol)s, %(continuous_symbol)s, %(strategy)s, %(timeframe)s, %(trade_source)s,
            %(side)s, %(qty)s, %(price)s,
            %(reason)s, %(source)s, %(event_type)s, %(ts)s,
            %(snapshot)s
        )
        ON CONFLICT (trade_id, event_type)
        DO UPDATE SET
            db_trade_id = EXCLUDED.db_trade_id,
            run_id = EXCLUDED.run_id,
            symbol = EXCLUDED.symbol,
            continuous_symbol = EXCLUDED.continuous_symbol,
            strategy = EXCLUDED.strategy,
            timeframe = EXCLUDED.timeframe,
            side = EXCLUDED.side,
            qty = EXCLUDED.qty,
            price = EXCLUDED.price,
            reason = EXCLUDED.reason,
            source = EXCLUDED.source,
            ts = EXCLUDED.ts,
            snapshot = EXCLUDED.snapshot,
            updated_at = now();
        """

        params = {
            "trade_id": item.trade_id,
            "db_trade_id": item.db_trade_id,
            "run_id": item.run_id,
            "symbol": item.symbol,
            "continuous_symbol": item.continuous_symbol,
            "strategy": item.strategy,
            "timeframe": item.timeframe,
            "trade_source": "paper",
            "side": item.side,
            "qty": item.qty,
            "price": item.price,
            "reason": item.reason,
            "source": item.source,
            "event_type": item.event_type,
            "ts": item.ts,
            "snapshot": Jsonb(item.snapshot or {}),
        }

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
