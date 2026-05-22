from __future__ import annotations

import psycopg
from dataclasses import dataclass

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class FuturesMtfRegime:
    symbol: str
    root_symbol: str
    macro_timeframe: str
    execution_timeframe: str
    macro_regime: str
    execution_regime: str
    macro_trend: str
    execution_trend: str
    volatility_state: str
    bias_alignment: str
    tradable: bool
    reason: str


class FuturesMtfRegimeAggregator:
    """
    Русский комментарий:
    Агрегирует futures regime по нескольким таймфреймам:
    H1 = macro bias, M15 = structure, M5 = execution trigger.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS futures_mtf_regime (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            root_symbol TEXT NOT NULL,
            macro_timeframe TEXT NOT NULL DEFAULT 'H1',
            structure_timeframe TEXT NOT NULL DEFAULT 'M15',
            execution_timeframe TEXT NOT NULL DEFAULT 'M5',

            macro_regime TEXT NOT NULL DEFAULT 'unknown',
            structure_regime TEXT NOT NULL DEFAULT 'unknown',
            execution_regime TEXT NOT NULL DEFAULT 'unknown',

            macro_trend TEXT NOT NULL DEFAULT 'unknown',
            structure_trend TEXT NOT NULL DEFAULT 'unknown',
            execution_trend TEXT NOT NULL DEFAULT 'unknown',

            volatility_state TEXT NOT NULL DEFAULT 'unknown',
            bias_alignment TEXT NOT NULL DEFAULT 'unknown',
            tradable BOOLEAN NOT NULL DEFAULT FALSE,
            reason TEXT NOT NULL DEFAULT '',

            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE(symbol)
        );

        CREATE INDEX IF NOT EXISTS idx_futures_mtf_regime_root
        ON futures_mtf_regime(root_symbol, tradable);
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def _latest_regime(self, cur, symbol: str, timeframe: str) -> dict:
        cur.execute(
            """
            SELECT regime, trend, volatility, atr, ts
            FROM regime_snapshots
            WHERE symbol=%s
              AND timeframe=%s
            ORDER BY ts DESC
            LIMIT 1
            """,
            (symbol, timeframe),
        )
        row = cur.fetchone()

        if not row:
            return {
                "regime": "unknown",
                "trend": "unknown",
                "volatility": "unknown",
                "atr": 0.0,
            }

        return {
            "regime": str(row[0] or "unknown"),
            "trend": str(row[1] or "unknown"),
            "volatility": str(row[2] or "unknown"),
            "atr": float(row[3] or 0.0),
        }

    def calculate_symbol(
        self,
        *,
        symbol: str,
        macro_tf: str = "H1",
        structure_tf: str = "M15",
        execution_tf: str = "M5",
    ) -> FuturesMtfRegime:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT root_symbol
                    FROM futures_context_snapshots
                    WHERE contract_symbol=%s
                    LIMIT 1
                    """,
                    (symbol,),
                )
                root_row = cur.fetchone()
                root = str(root_row[0]) if root_row else symbol

                macro = self._latest_regime(cur, symbol, macro_tf)
                structure = self._latest_regime(cur, symbol, structure_tf)
                execution = self._latest_regime(cur, symbol, execution_tf)

        trends = [macro["trend"], structure["trend"], execution["trend"]]
        vols = [macro["volatility"], structure["volatility"], execution["volatility"]]

        if "unknown" in trends:
            alignment = "unknown"
            tradable = False
            reason = "missing_timeframe_regime"
        elif macro["trend"] == execution["trend"] and macro["trend"] in ("up", "down"):
            alignment = "aligned"
            tradable = True
            reason = "macro_execution_trend_aligned"
        elif macro["trend"] == "flat" and execution["regime"] in ("range", "compression"):
            alignment = "range_aligned"
            tradable = True
            reason = "flat_macro_range_execution"
        else:
            alignment = "conflict"
            tradable = False
            reason = "macro_execution_conflict"

        if "high" in vols:
            volatility_state = "high"
        elif "normal" in vols:
            volatility_state = "normal"
        elif all(v == "low" for v in vols):
            volatility_state = "low"
        else:
            volatility_state = "unknown"

        return FuturesMtfRegime(
            symbol=symbol,
            root_symbol=root,
            macro_timeframe=macro_tf,
            execution_timeframe=execution_tf,
            macro_regime=macro["regime"],
            execution_regime=execution["regime"],
            macro_trend=macro["trend"],
            execution_trend=execution["trend"],
            volatility_state=volatility_state,
            bias_alignment=alignment,
            tradable=tradable,
            reason=reason,
        )

    def save(self, item: FuturesMtfRegime, structure_tf: str = "M15") -> None:
        sql = """
        INSERT INTO futures_mtf_regime (
            symbol,
            root_symbol,
            macro_timeframe,
            structure_timeframe,
            execution_timeframe,
            macro_regime,
            execution_regime,
            macro_trend,
            execution_trend,
            volatility_state,
            bias_alignment,
            tradable,
            reason,
            calculated_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
        ON CONFLICT (symbol)
        DO UPDATE SET
            root_symbol = EXCLUDED.root_symbol,
            macro_timeframe = EXCLUDED.macro_timeframe,
            structure_timeframe = EXCLUDED.structure_timeframe,
            execution_timeframe = EXCLUDED.execution_timeframe,
            macro_regime = EXCLUDED.macro_regime,
            execution_regime = EXCLUDED.execution_regime,
            macro_trend = EXCLUDED.macro_trend,
            execution_trend = EXCLUDED.execution_trend,
            volatility_state = EXCLUDED.volatility_state,
            bias_alignment = EXCLUDED.bias_alignment,
            tradable = EXCLUDED.tradable,
            reason = EXCLUDED.reason,
            calculated_at = now()
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        item.symbol,
                        item.root_symbol,
                        item.macro_timeframe,
                        structure_tf,
                        item.execution_timeframe,
                        item.macro_regime,
                        item.execution_regime,
                        item.macro_trend,
                        item.execution_trend,
                        item.volatility_state,
                        item.bias_alignment,
                        item.tradable,
                        item.reason,
                    ),
                )
            conn.commit()
