from __future__ import annotations

import os
from decimal import Decimal


class PaperMtmSnapshotRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql:///finam_core")

    def insert_snapshot(
        self,
        *,
        candidate_id: int,
        strategy_code: str,
        symbol: str,
        timeframe: str,
        trades: int,
        gross_pnl: Decimal,
        commission: Decimal,
        exchange_fee: Decimal,
        clearing_fee: Decimal,
        slippage: Decimal,
        net_trading_pnl: Decimal,
        estimated_tax: Decimal,
        net_after_tax: Decimal,
        max_drawdown: Decimal,
        market_model_version: str,
        source_version: str,
    ) -> None:
        import psycopg2

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analytics.paper_portfolio_mtm_snapshot_v1 (
                        candidate_id, strategy_code, symbol, timeframe, trades,
                        gross_pnl, commission, exchange_fee, clearing_fee, slippage,
                        net_trading_pnl, estimated_tax, net_after_tax, max_drawdown,
                        market_model_version, source_version
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        candidate_id, strategy_code, symbol, timeframe, trades,
                        gross_pnl, commission, exchange_fee, clearing_fee, slippage,
                        net_trading_pnl, estimated_tax, net_after_tax, max_drawdown,
                        market_model_version, source_version,
                    ),
                )
