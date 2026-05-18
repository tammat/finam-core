# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
from typing import Any

from finam_core.analytics.closed_trade_engine import ClosedTrade


class ClosedTradeRepository:
    def __init__(self, conn: Any):
        self.conn = conn

    def save_closed_trades(self, trades: list[ClosedTrade], trade_source: str = "paper") -> int:
        saved = 0

        with self.conn.cursor() as cur:
            for t in trades:
                cur.execute(
                    """
                    INSERT INTO closed_trades (
                        signal_id, symbol, side, entry_ts, exit_ts, qty,
                        entry_price, exit_price,
                        gross_pnl, commission, net_pnl,
                        horizon, strategy, regime,
                        trade_source, payload
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        t.signal_id,
                        t.symbol,
                        t.side,
                        t.entry_ts,
                        t.exit_ts,
                        t.qty,
                        t.entry_price,
                        t.exit_price,
                        t.gross_pnl,
                        t.commission,
                        t.net_pnl,
                        t.horizon,
                        t.strategy,
                        t.regime,
                        trade_source,
                        json.dumps(
                            {
                                **t.__dict__,
                                "replay_campaign_id": os.getenv("REPLAY_CAMPAIGN_ID"),
                                "replay_id": os.getenv("REPLAY_ID"),
                                "replay_symbol": os.getenv("REPLAY_SYMBOL"),
                                "replay_timeframe": os.getenv("REPLAY_TIMEFRAME"),
                                "replay_strategy": os.getenv("REPLAY_STRATEGY"),
                                "dataset_source": "replay_campaign" if os.getenv("REPLAY_CAMPAIGN_ID") else "runtime",
                            },
                            ensure_ascii=False,
                            default=str,
                        ),
                    ),
                )
                saved += cur.rowcount

        self.conn.commit()
        return saved
