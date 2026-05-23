from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.ng_regime_v2 import NgRegimeFeaturesV2, classify_ng_regime_v2


def safe_float(v, default=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="NG_CONSERVATIVE_BREAKOUT")
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ng_regime_v2_trade_analytics (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    session_bucket TEXT NOT NULL,
                    regime_v2 TEXT NOT NULL,
                    trades INTEGER NOT NULL,
                    gross_profit NUMERIC NOT NULL,
                    gross_loss NUMERIC NOT NULL,
                    profit_factor NUMERIC NOT NULL,
                    expectancy NUMERIC NOT NULL,
                    winrate NUMERIC NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, session_bucket, regime_v2)
                );
            """)

            cur.execute("""
                SELECT symbol, strategy, timeframe, payload
                FROM trades
                WHERE strategy=%s
                  AND trade_source='paper'
                  AND symbol LIKE 'NG%%'
                  AND payload->>'role' = 'exit'
            """, (args.strategy,))

            groups = {}

            for symbol, strategy, timeframe, payload in cur.fetchall():
                payload = payload or {}

                session_bucket = payload.get("session_bucket") or "UNKNOWN_SESSION"

                f = NgRegimeFeaturesV2(
                    atr_percent=safe_float(payload.get("atr_percent")),
                    atr_expansion=safe_float(payload.get("atr_expansion"), 1.0),
                    range_expansion=safe_float(payload.get("range_expansion"), 1.0),
                    ema_slope=safe_float(payload.get("ema_slope")),
                    compression_score=safe_float(payload.get("compression_score")),
                    breakout_strength=safe_float(payload.get("breakout_strength"), 1.0),
                    session_bucket=session_bucket,
                )

                regime_v2 = classify_ng_regime_v2(f)
                pnl = safe_float(payload.get("realized_pnl"))

                key = (symbol, strategy, timeframe, session_bucket, regime_v2)
                groups.setdefault(key, []).append(pnl)

            saved = 0

            for key, pnls in groups.items():
                symbol, strategy, timeframe, session_bucket, regime_v2 = key

                wins = [x for x in pnls if x > 0]
                losses = [x for x in pnls if x < 0]

                gross_profit = sum(wins)
                gross_loss = abs(sum(losses))
                pf = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
                expectancy = sum(pnls) / len(pnls) if pnls else 0.0
                winrate = len(wins) / len(pnls) if pnls else 0.0

                cur.execute("""
                    INSERT INTO ng_regime_v2_trade_analytics (
                        symbol, strategy, timeframe, session_bucket, regime_v2,
                        trades, gross_profit, gross_loss,
                        profit_factor, expectancy, winrate, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT(symbol, strategy, timeframe, session_bucket, regime_v2)
                    DO UPDATE SET
                        trades=EXCLUDED.trades,
                        gross_profit=EXCLUDED.gross_profit,
                        gross_loss=EXCLUDED.gross_loss,
                        profit_factor=EXCLUDED.profit_factor,
                        expectancy=EXCLUDED.expectancy,
                        winrate=EXCLUDED.winrate,
                        calculated_at=now()
                """, (
                    symbol, strategy, timeframe, session_bucket, regime_v2,
                    len(pnls), gross_profit, gross_loss, pf, expectancy, winrate,
                ))

                print(
                    "NG_REGIME_V2_ANALYTICS "
                    f"symbol={symbol} session={session_bucket} regime={regime_v2} "
                    f"trades={len(pnls)} pf={round(pf, 4)} expectancy={round(expectancy, 6)}",
                    flush=True,
                )
                saved += 1

        conn.commit()

    print(f"NG_REGIME_V2_ANALYTICS_SUMMARY rows={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
