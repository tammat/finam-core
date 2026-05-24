from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg

from finam_core.research.intermarket_regime import (
    IntermarketInput,
    classify_intermarket_regime,
)


@dataclass(frozen=True)
class SymbolImpulse:
    symbol: str
    impulse: float


ROOT_MAP = {
    "BR": ["BRM6@RTSX", "BRN6@RTSX", "BRQ6@RTSX"],
    "NG": ["NGM6@RTSX", "NGN6@RTSX", "NGQ6@RTSX"],
    "GOLD": ["GDM6@RTSX", "GDU6@RTSX", "GLM6@RTSX", "GLU6@RTSX"],
    "SILVER": ["SVM6@RTSX", "SVU6@RTSX"],
    "USDRUB": ["USDRUBF@RTSX"],
    "CNY": ["CNYRUBF@RTSX", "CNYRUB_TOM@MISX"],
}


def _impulse_for_root(conn, *, root: str, timeframe: str, lookback_bars: int) -> float:
    symbols = ROOT_MAP[root]

    sql = """
    WITH ranked AS (
        SELECT
            symbol,
            ts,
            close,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY ts DESC) AS rn
        FROM market_bars
        WHERE symbol = ANY(%(symbols)s)
          AND timeframe = %(timeframe)s
          AND close IS NOT NULL
    ),
    latest AS (
        SELECT symbol, close AS latest_close
        FROM ranked
        WHERE rn = 1
    ),
    previous AS (
        SELECT symbol, close AS previous_close
        FROM ranked
        WHERE rn = %(lookback_bars)s
    )
    SELECT
        AVG(
            CASE
                WHEN p.previous_close IS NULL OR p.previous_close = 0 THEN 0
                ELSE (l.latest_close - p.previous_close) / p.previous_close
            END
        )::float AS impulse
    FROM latest l
    LEFT JOIN previous p ON p.symbol = l.symbol;
    """

    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "symbols": symbols,
                "timeframe": timeframe,
                "lookback_bars": lookback_bars,
            },
        )
        row = cur.fetchone()

    if not row or row[0] is None:
        return 0.0

    # Русский комментарий: масштабируем малые доходности до score, но ограничиваем в classifier.
    return float(row[0]) * 100.0


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    timeframe = os.getenv("INTERMARKET_TIMEFRAME", "M5")
    lookback_bars = int(os.getenv("INTERMARKET_LOOKBACK_BARS", "12"))

    with psycopg.connect(database_url) as conn:
        br = _impulse_for_root(conn, root="BR", timeframe=timeframe, lookback_bars=lookback_bars)
        ng = _impulse_for_root(conn, root="NG", timeframe=timeframe, lookback_bars=lookback_bars)
        gold = _impulse_for_root(conn, root="GOLD", timeframe=timeframe, lookback_bars=lookback_bars)
        silver = _impulse_for_root(conn, root="SILVER", timeframe=timeframe, lookback_bars=lookback_bars)
        usdrub = _impulse_for_root(conn, root="USDRUB", timeframe=timeframe, lookback_bars=lookback_bars)
        cny = _impulse_for_root(conn, root="CNY", timeframe=timeframe, lookback_bars=lookback_bars)

        regime = classify_intermarket_regime(
            IntermarketInput(
                br_score=br,
                ng_score=ng,
                gold_score=gold,
                silver_score=silver,
                usdrub_score=usdrub,
                cny_score=cny,
            )
        )

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO intermarket_regime_snapshots (
                    timeframe,
                    br_score,
                    ng_score,
                    gold_score,
                    silver_score,
                    usdrub_score,
                    cny_score,
                    commodity_score,
                    fx_stress_score,
                    risk_mode,
                    commodity_mode,
                    confidence,
                    reason
                )
                VALUES (
                    %(timeframe)s,
                    %(br_score)s,
                    %(ng_score)s,
                    %(gold_score)s,
                    %(silver_score)s,
                    %(usdrub_score)s,
                    %(cny_score)s,
                    %(commodity_score)s,
                    %(fx_stress_score)s,
                    %(risk_mode)s,
                    %(commodity_mode)s,
                    %(confidence)s,
                    %(reason)s
                );
                """,
                {
                    "timeframe": timeframe,
                    "br_score": regime.br_score,
                    "ng_score": regime.ng_score,
                    "gold_score": regime.gold_score,
                    "silver_score": regime.silver_score,
                    "usdrub_score": regime.usdrub_score,
                    "cny_score": regime.cny_score,
                    "commodity_score": regime.commodity_score,
                    "fx_stress_score": regime.fx_stress_score,
                    "risk_mode": regime.risk_mode,
                    "commodity_mode": regime.commodity_mode,
                    "confidence": regime.confidence,
                    "reason": regime.reason,
                },
            )

        conn.commit()

    print(
        "INTERMARKET_REGIME_SNAPSHOT_OK "
        f"timeframe={timeframe} "
        f"risk_mode={regime.risk_mode} "
        f"commodity_mode={regime.commodity_mode} "
        f"confidence={regime.confidence}",
        flush=True,
    )


if __name__ == "__main__":
    main()
