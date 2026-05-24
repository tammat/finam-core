from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def safe_float(v, default=0.0):
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
                CREATE TABLE IF NOT EXISTS ng_session_regime_matrix (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    session_bucket TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    trades INTEGER NOT NULL,
                    gross_profit NUMERIC NOT NULL,
                    gross_loss NUMERIC NOT NULL,
                    profit_factor NUMERIC NOT NULL,
                    expectancy NUMERIC NOT NULL,
                    winrate NUMERIC NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, session_bucket, regime)
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
                regime = payload.get("regime") or "UNKNOWN_REGIME"
                pnl = safe_float(payload.get("realized_pnl", 0))

                key = (symbol, strategy, timeframe, session_bucket, regime)
                groups.setdefault(key, []).append(pnl)

            saved = 0

            for key, pnls in groups.items():
                symbol, strategy, timeframe, session_bucket, regime = key

                wins = [x for x in pnls if x > 0]
                losses = [x for x in pnls if x < 0]

                gross_profit = sum(wins)
                gross_loss = abs(sum(losses))
                pf = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
                expectancy = sum(pnls) / len(pnls) if pnls else 0.0
                winrate = len(wins) / len(pnls) if pnls else 0.0

                cur.execute("""
                    INSERT INTO ng_session_regime_matrix (
                        symbol, strategy, timeframe, session_bucket, regime,
                        trades, gross_profit, gross_loss,
                        profit_factor, expectancy, winrate, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT(symbol, strategy, timeframe, session_bucket, regime)
                    DO UPDATE SET
                        trades=EXCLUDED.trades,
                        gross_profit=EXCLUDED.gross_profit,
                        gross_loss=EXCLUDED.gross_loss,
                        profit_factor=EXCLUDED.profit_factor,
                        expectancy=EXCLUDED.expectancy,
                        winrate=EXCLUDED.winrate,
                        calculated_at=now()
                """, (
                    symbol, strategy, timeframe, session_bucket, regime,
                    len(pnls), gross_profit, gross_loss, pf, expectancy, winrate,
                ))

                print(
                    "NG_SESSION_REGIME_MATRIX "
                    f"symbol={symbol} session={session_bucket} regime={regime} "
                    f"trades={len(pnls)} pf={round(pf, 4)} expectancy={round(expectancy, 6)}",
                    flush=True,
                )
                saved += 1

        conn.commit()

    print(f"NG_SESSION_REGIME_MATRIX_SUMMARY rows={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
