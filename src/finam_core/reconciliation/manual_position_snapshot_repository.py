# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from typing import Any

from finam_core.reconciliation.manual_trade_reconciliation import BrokerPositionSnapshot


class ManualPositionSnapshotRepository:
    def __init__(self, conn: Any):
        self.conn = conn

    def save_positions(self, positions: list[BrokerPositionSnapshot]) -> int:
        count = 0

        with self.conn.cursor() as cur:
            for p in positions:
                cur.execute(
                    """
                    INSERT INTO manual_broker_position_snapshots (
                        symbol,
                        qty,
                        average_price,
                        current_price,
                        unrealized_pnl,
                        source,
                        payload
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)
                    """,
                    (
                        p.symbol,
                        p.qty,
                        p.average_price,
                        p.current_price,
                        p.unrealized_pnl,
                        "finam_api",
                        json.dumps(p.__dict__, ensure_ascii=False, default=str),
                    ),
                )
                count += 1

        self.conn.commit()
        return count
