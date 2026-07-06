from __future__ import annotations

import os
from datetime import datetime

import psycopg2
import psycopg2.extras


class MarketModelRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql:///finam_core")

    def load_raw(
        self,
        symbol: str,
        broker_code: str,
        account_scope: str,
        snapshot_ts: datetime | None = None,
    ) -> dict:
        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        i.symbol,
                        i.instrument_name,
                        i.exchange_code,
                        i.asset_class,
                        i.currency_code,
                        i.is_active,
                        i.eligibility_scope,
                        i.source_version AS instrument_source_version,

                        cs.lot_size,
                        cs.tick_size,
                        cs.tick_value,
                        cs.contract_multiplier,
                        cs.price_precision,
                        cs.source_version AS contract_source_version,

                        bf.broker_fee_code,
                        bf.broker_code,
                        bf.commission_per_trade,
                        bf.commission_pct,

                        ef.exchange_fee_code,
                        ef.exchange_fee_per_trade,
                        ef.clearing_fee_per_trade,

                        sp.slippage_profile_code,
                        sp.slippage_per_trade,

                        tp.tax_profile_code,
                        tp.tax_rate
                    FROM analytics.market_instrument_v1 i
                    JOIN analytics.market_contract_spec_v1 cs
                      ON cs.symbol=i.symbol
                     AND cs.is_active=true
                    JOIN analytics.broker_fee_profile_v1 bf
                      ON bf.exchange_code=i.exchange_code
                     AND bf.asset_class=i.asset_class
                     AND bf.broker_code=%s
                     AND bf.is_active=true
                    JOIN analytics.exchange_fee_profile_v1 ef
                      ON ef.exchange_code=i.exchange_code
                     AND ef.asset_class=i.asset_class
                     AND ef.is_active=true
                    JOIN analytics.slippage_profile_v1 sp
                      ON sp.exchange_code=i.exchange_code
                     AND sp.asset_class=i.asset_class
                     AND sp.liquidity_bucket='DEFAULT'
                     AND sp.is_active=true
                    JOIN analytics.account_tax_profile_v1 tp
                      ON tp.account_scope=%s
                     AND tp.is_active=true
                    WHERE i.symbol=%s
                      AND i.is_active=true
                    ORDER BY cs.valid_from DESC
                    LIMIT 1
                    """,
                    (broker_code, account_scope, symbol),
                )
                row = cur.fetchone()

        if not row:
            raise LookupError(f"MARKET_MODEL_NOT_FOUND symbol={symbol}")

        return dict(row)
