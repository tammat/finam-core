from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from finam_core.analytics.statistics_repository import build_psycopg_url


class RuntimeGuardPreSignalBlockAuditV1:
    """
    Русский комментарий:
    Сохраняет причины, по которым рынок не дошёл до signal/intent.
    Не влияет на execution/risk/OMS.
    """

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL") or build_psycopg_url()

    def migrate(self) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS runtime_guard_pre_signal_block_audit_v1 (
                    id BIGSERIAL PRIMARY KEY,
                    ts TIMESTAMPTZ NOT NULL DEFAULT now(),

                    symbol TEXT NOT NULL,
                    strategy TEXT,
                    timeframe TEXT,

                    block_type TEXT NOT NULL,
                    block_reason TEXT NOT NULL,

                    price DOUBLE PRECISION,
                    atr DOUBLE PRECISION,
                    atr_pct DOUBLE PRECISION,
                    threshold DOUBLE PRECISION,
                    compression_ratio DOUBLE PRECISION,

                    regime TEXT,
                    trend TEXT,
                    volatility TEXT,

                    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """)

                cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_runtime_guard_pre_signal_block_audit_v1_symbol_ts
                ON runtime_guard_pre_signal_block_audit_v1(symbol, ts DESC);
                """)

                cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_runtime_guard_pre_signal_block_audit_v1_type
                ON runtime_guard_pre_signal_block_audit_v1(block_type, block_reason);
                """)

            conn.commit()

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except Exception:
            return None

    def save(
        self,
        *,
        symbol: str,
        block_type: str,
        block_reason: str,
        strategy: str | None = None,
        timeframe: str | None = None,
        price: Any = None,
        atr: Any = None,
        atr_pct: Any = None,
        threshold: Any = None,
        compression_ratio: Any = None,
        regime: str | None = None,
        trend: str | None = None,
        volatility: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        payload = payload if isinstance(payload, dict) else {}

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO runtime_guard_pre_signal_block_audit_v1 (
                    symbol,
                    strategy,
                    timeframe,
                    block_type,
                    block_reason,
                    price,
                    atr,
                    atr_pct,
                    threshold,
                    compression_ratio,
                    regime,
                    trend,
                    volatility,
                    payload
                )
                VALUES (
                    %(symbol)s,
                    %(strategy)s,
                    %(timeframe)s,
                    %(block_type)s,
                    %(block_reason)s,
                    %(price)s,
                    %(atr)s,
                    %(atr_pct)s,
                    %(threshold)s,
                    %(compression_ratio)s,
                    %(regime)s,
                    %(trend)s,
                    %(volatility)s,
                    %(payload)s
                )
                """, {
                    "symbol": symbol,
                    "strategy": strategy,
                    "timeframe": timeframe,
                    "block_type": block_type,
                    "block_reason": block_reason,
                    "price": self._float_or_none(price),
                    "atr": self._float_or_none(atr),
                    "atr_pct": self._float_or_none(atr_pct),
                    "threshold": self._float_or_none(threshold),
                    "compression_ratio": self._float_or_none(compression_ratio),
                    "regime": regime,
                    "trend": trend,
                    "volatility": volatility,
                    "payload": Jsonb(payload),
                })

            conn.commit()

        print(
            "RUNTIME_GUARD_PRE_SIGNAL_BLOCK_SAVED "
            f"symbol={symbol} "
            f"block_type={block_type} "
            f"reason={block_reason}",
            flush=True,
        )
